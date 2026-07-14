<?php
// send_rezept.php
// Handles website prescription order submissions using authenticated SMTP.

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: /');
    exit;
}

// ==========================================
// KONFIGURATION (Microsoft Office 365 / Graph API)
// ==========================================
require_once __DIR__ . '/credentials.php';
define('FROM_NAME', 'Praxis-Website');
// ==========================================

// 1. Get and sanitize input fields
$vorname = isset($_POST['vorname']) ? strip_tags(trim($_POST['vorname'])) : '';
$nachname = isset($_POST['nachname']) ? strip_tags(trim($_POST['nachname'])) : '';
$geburtsdatum = isset($_POST['geburtsdatum']) ? strip_tags(trim($_POST['geburtsdatum'])) : '';
$email = isset($_POST['email']) ? filter_var(trim($_POST['email']), FILTER_VALIDATE_EMAIL) : '';
$medikament = isset($_POST['medikament']) ? strip_tags(trim($_POST['medikament'])) : '';
$einwilligung = isset($_POST['einwilligung']) ? true : false;

// Honeypot spam prevention
$hp_website = isset($_POST['website']) ? trim($_POST['website']) : '';
$hp_nickname = isset($_POST['nickname']) ? trim($_POST['nickname']) : '';
$hp_phone_work = isset($_POST['phone_work']) ? trim($_POST['phone_work']) : '';

if ($hp_website !== '' || $hp_nickname !== '' || $hp_phone_work !== '') {
    // Silent success redirect to trick spam bots
    header('Location: /danke/');
    exit;
}

// 2. Simple validation
if (empty($vorname) || empty($nachname) || empty($geburtsdatum) || empty($medikament) || !$einwilligung) {
    http_response_code(400);
    die("Bitte füllen Sie alle Pflichtfelder aus und stimmen Sie der Datenschutzerklärung zu.");
}

$subject = "Neue Rezeptbestellung via Website von " . $vorname . " " . $nachname;

// Email body in HTML format
$message = "
<html>
<head>
  <title>Neue Rezeptbestellung</title>
</head>
<body style='font-family: sans-serif; color: #333; line-height: 1.5;'>
  <h2 style='color: #8fae70;'>Rezeptbestellung Online-Formular</h2>
  <p>Es wurde eine neue Rezeptbestellung über das Formular der Website übermittelt:</p>
  
  <table style='border: 1px solid #ddd; border-collapse: collapse; width: 100%; max-width: 600px;'>
    <tr style='background: #f9f9f9;'>
      <td style='padding: 10px; border: 1px solid #ddd; font-weight: bold; width: 180px;'>Vorname:</td>
      <td style='padding: 10px; border: 1px solid #ddd;'>$vorname</td>
    </tr>
    <tr>
      <td style='padding: 10px; border: 1px solid #ddd; font-weight: bold;'>Nachname:</td>
      <td style='padding: 10px; border: 1px solid #ddd;'>$nachname</td>
    </tr>
    <tr style='background: #f9f9f9;'>
      <td style='padding: 10px; border: 1px solid #ddd; font-weight: bold;'>Geburtsdatum:</td>
      <td style='padding: 10px; border: 1px solid #ddd;'>$geburtsdatum</td>
    </tr>
    <tr>
      <td style='padding: 10px; border: 1px solid #ddd; font-weight: bold;'>E-Mail:</td>
      <td style='padding: 10px; border: 1px solid #ddd;'>" . ($email ? $email : 'Keine E-Mail-Adresse angegeben') . "</td>
    </tr>
    <tr style='background: #f9f9f9;'>
      <td style='padding: 10px; border: 1px solid #ddd; font-weight: bold; vertical-align: top;'>Gewünschtes Medikament:</td>
      <td style='padding: 10px; border: 1px solid #ddd; white-space: pre-wrap;'>$medikament</td>
    </tr>
  </table>
  
  <p style='font-size: 12px; color: #666; margin-top: 20px;'>
    Einwilligungserklärung gemäß DSGVO in die Datenverarbeitung wurde durch Auswählen der Checkbox erteilt.
  </p>
</body>
</html>
";

function log_error($msg) {
    error_log($msg);
    $log_file = __DIR__ . '/mail_error.log';
    $timestamp = date('[Y-m-d H:i:s] ');
    file_put_contents($log_file, $timestamp . $msg . "\n", FILE_APPEND);
}

/**
 * Holt einen Access Token von der Microsoft Identity Platform via Delegated Permissions / Refresh Token Flow.
 */
function get_graph_access_token_by_refresh($tenant_id, $client_id, $client_secret) {
    $token_file = __DIR__ . '/refresh_token.php';
    if (!file_exists($token_file)) {
        log_error("Microsoft Graph Auth Error: refresh_token.php not found.");
        return null;
    }
    
    $refresh_token = include $token_file;
    if (empty($refresh_token)) {
        log_error("Microsoft Graph Auth Error: refresh_token is empty.");
        return null;
    }
    
    $url = "https://login.microsoftonline.com/" . $tenant_id . "/oauth2/v2.0/token";
    $post_data = http_build_query([
        'grant_type' => 'refresh_token',
        'client_id' => $client_id,
        'client_secret' => $client_secret,
        'refresh_token' => $refresh_token,
        'scope' => 'https://graph.microsoft.com/.default'
    ]);
    
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $post_data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded'
    ]);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code !== 200 || !$response) {
        log_error("Microsoft Graph Auth Error (HTTP $http_code): " . $response);
        return null;
    }
    
    $data = json_decode($response, true);
    
    // Microsoft can return a new refresh token. If so, write it back to keep it updated.
    if (isset($data['refresh_token']) && $data['refresh_token'] !== $refresh_token) {
        $php_content = "<?php\nreturn '" . addslashes($data['refresh_token']) . "';\n";
        file_put_contents($token_file, $php_content);
    }
    
    return isset($data['access_token']) ? $data['access_token'] : null;
}

/**
 * Sendet eine E-Mail über die Microsoft Graph API.
 */
function send_graph_mail($access_token, $from_email, $to_email, $subject, $message_html) {
    $url = "https://graph.microsoft.com/v1.0/users/" . urlencode($from_email) . "/sendMail";
    
    $payload = [
        'message' => [
            'subject' => $subject,
            'body' => [
                'contentType' => 'HTML',
                'content' => $message_html
            ],
            'toRecipients' => [
                [
                    'emailAddress' => [
                        'address' => $to_email
                    ]
                ]
            ]
        ],
        'saveToSentItems' => 'false'
    ];
    
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . $access_token,
        'Content-Type: application/json'
    ]);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    // Graph sendMail API returns 202 Accepted on success
    if ($http_code === 202) {
        return true;
    }
    
    log_error("Microsoft Graph sendMail Error (HTTP $http_code): " . $response);
    return false;
}

// 3. Send email using Microsoft Graph API with Delegated Refresh Token Flow
$access_token = get_graph_access_token_by_refresh(O365_TENANT_ID, O365_CLIENT_ID, O365_CLIENT_SECRET);
if ($access_token && send_graph_mail($access_token, FROM_EMAIL, MAIL_TO, $subject, $message)) {
    header('Location: /danke/');
    exit;
} else {
    http_response_code(500);
    echo "Es gab einen Fehler beim Senden der Rezeptbestellung. Bitte versuchen Sie es später noch einmal oder kontaktieren Sie uns direkt.";
}
?>
