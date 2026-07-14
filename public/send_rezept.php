<?php
// send_rezept.php
// PHP script to handle website prescription order submissions on All-Inkl.

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    // Redirect to home if accessed directly
    header('Location: /');
    exit;
}

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

// 3. Email configuration
// Change this email address to your Exchange / Office 365 reception address!
$to = "info@praxis-dr-ertl.de"; 
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

// Headers setup
$headers = "MIME-Version: 1.0" . "\r\n";
$headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
$headers .= "From: rezeptformular@praxis-dr-ertl.de" . "\r\n"; // Must be an email address from your domain on All-Inkl

// Send email
if (mail($to, $subject, $message, $headers)) {
    // Redirect to relative /danke/ folder path on success
    header('Location: /danke/');
    exit;
} else {
    http_response_code(500);
    echo "Es gab einen Fehler beim Senden der Rezeptbestellung. Bitte versuchen Sie es später noch einmal oder kontaktieren Sie uns direkt.";
}
?>
