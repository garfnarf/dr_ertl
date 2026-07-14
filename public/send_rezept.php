<?php
// send_rezept.php
// Handles website prescription order submissions using authenticated SMTP.

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: /');
    exit;
}

// ==========================================
// KONFIGURATION (Bitte hier Ihre Daten eintragen)
// ==========================================
define('SMTP_HOST', 'smtp.hosteurope.de');       // SMTP-Server von Host Europe
define('SMTP_PORT', 587);                        // 587 (für TLS-Verschlüsselung) oder 465 (für SSL)
define('SMTP_USER', 'rezeptformular@praxis-dr-ertl.de'); // Der Benutzername Ihres Postfachs bei Host Europe
define('SMTP_PASS', 'IHR_POSTFACH_PASSWORT');    // Das Passwort des Postfachs
define('MAIL_TO', 'info@praxis-dr-ertl.de');      // Die Empfänger-Adresse (Ihr Exchange / O365 Postfach)
define('FROM_EMAIL', 'rezeptformular@praxis-dr-ertl.de'); // Muss dem SMTP-Postfach entsprechen
define('FROM_NAME', 'Praxis-Website');
// ==========================================

// 1. Get and sanitize input fields
$vorname = isset($_POST['vorname']) ? strip_tags(trim($_POST['vorname'])) : '';
$nachname = isset($_POST['nachname']) ? strip_tags(trim($_POST['nachname'])) : '';
$geburtsdatum = isset($_POST['geburtsdatum']) ? strip_tags(trim($_POST['geburtsdatum'])) : '';
$email = isset($_POST['email']) ? filter_var(trim($_POST['email']), FILTER_VALIDATE_EMAIL) : '';
$medikament = isset($_POST['medikament']) ? strip_tags(trim($_POST['medikament'])) : '';
$einwilligung = isset($_POST['einwilligung']) ? true : false;

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

// SMTP socket connection helper function
function send_smtp_mail($to, $subject, $message_html, $from_email, $from_name, $smtp_host, $smtp_username, $smtp_password, $smtp_port) {
    $is_ssl = ($smtp_port == 465);
    $socket = fsockopen(($is_ssl ? "ssl://" : "") . $smtp_host, $smtp_port, $errno, $errstr, 15);
    if (!$socket) {
        return false;
    }
    
    fgets($socket, 515); // Greeting
    
    fwrite($socket, "EHLO " . $_SERVER['SERVER_NAME'] . "\r\n");
    while ($line = fgets($socket, 515)) {
        if (substr($line, 3, 1) == " ") break;
    }
    
    // STARTTLS negotiation for Port 587
    if ($smtp_port == 587) {
        fwrite($socket, "STARTTLS\r\n");
        $res = fgets($socket, 515);
        if (substr($res, 0, 3) != "220") {
            fclose($socket);
            return false;
        }
        stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT);
        
        // EHLO again after TLS negotiation
        fwrite($socket, "EHLO " . $_SERVER['SERVER_NAME'] . "\r\n");
        while ($line = fgets($socket, 515)) {
            if (substr($line, 3, 1) == " ") break;
        }
    }
    
    // Auth login
    fwrite($socket, "AUTH LOGIN\r\n");
    $res = fgets($socket, 515);
    if (substr($res, 0, 3) != "334") {
        fclose($socket);
        return false;
    }
    
    fwrite($socket, base64_encode($smtp_username) . "\r\n");
    $res = fgets($socket, 515);
    if (substr($res, 0, 3) != "334") {
        fclose($socket);
        return false;
    }
    
    fwrite($socket, base64_encode($smtp_password) . "\r\n");
    $res = fgets($socket, 515);
    if (substr($res, 0, 3) != "235") {
        fclose($socket);
        return false;
    }
    
    // MAIL FROM / RCPT TO / DATA
    fwrite($socket, "MAIL FROM:<" . $from_email . ">\r\n");
    fgets($socket, 515);
    
    fwrite($socket, "RCPT TO:<" . $to . ">\r\n");
    fgets($socket, 515);
    
    fwrite($socket, "DATA\r\n");
    fgets($socket, 515);
    
    // Headers construction
    $headers = "MIME-Version: 1.0\r\n";
    $headers .= "Content-Type: text/html; charset=UTF-8\r\n";
    $headers .= "From: =?UTF-8?B?" . base64_encode($from_name) . "?= <" . $from_email . ">\r\n";
    $headers .= "To: <" . $to . ">\r\n";
    $headers .= "Subject: =?UTF-8?B?" . base64_encode($subject) . "?=\r\n";
    $headers .= "Date: " . date('r') . "\r\n";
    
    fwrite($socket, $headers . "\r\n" . $message_html . "\r\n.\r\n");
    $res = fgets($socket, 515);
    
    fwrite($socket, "QUIT\r\n");
    fclose($socket);
    
    return substr($res, 0, 3) == "250";
}

// Send email using SMTP
if (send_smtp_mail(MAIL_TO, $subject, $message, FROM_EMAIL, FROM_NAME, SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_PORT)) {
    header('Location: /danke/');
    exit;
} else {
    http_response_code(500);
    echo "Es gab einen Fehler beim Senden der Rezeptbestellung. Bitte versuchen Sie es später noch einmal oder kontaktieren Sie uns direkt.";
}
?>
