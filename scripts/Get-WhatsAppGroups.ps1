<#
.SYNOPSIS
    Retrieve all WhatsApp group IDs from a Green API instance.

.DESCRIPTION
    Calls the Green API getContacts endpoint and filters the results to show
    only WhatsApp groups (chatId ending in @g.us). Use the displayed IDs to
    configure the WHATSAPP_GROUP_* variables in your .env file.

.PARAMETER InstanceId
    Your Green API instance ID (format: 1101XXXXXX). Found on the dashboard.

.PARAMETER ApiToken
    Your Green API API token. Found on the instance dashboard.

.EXAMPLE
    .\scripts\Get-WhatsAppGroups.ps1

.EXAMPLE
    .\scripts\Get-WhatsAppGroups.ps1 -InstanceId 1101123456 -ApiToken your_token_here
#>

param(
    [string]$InstanceId = "",
    [string]$ApiToken   = ""
)

if (-not $InstanceId) {
    $InstanceId = Read-Host "Instance ID (ex: 1101XXXXXX)"
}
if (-not $ApiToken) {
    $ApiToken = Read-Host "API Token"
}

$url = "https://api.green-api.com/waInstance$InstanceId/getContacts/$ApiToken"

Write-Host ""
Write-Host "Connexion a Green API..." -ForegroundColor Cyan

try {
    $contacts = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 15 -ErrorAction Stop
}
catch {
    $status = $_.Exception.Response.StatusCode.value__

    if ($status -eq 401 -or $status -eq 403) {
        Write-Host "Erreur d'authentification ($status) : verifiez votre InstanceId et votre ApiToken." -ForegroundColor Red
    }
    elseif ($status -eq 466) {
        Write-Host "Erreur 466 : l'instance Green API est hors ligne." -ForegroundColor Red
        Write-Host "Reconnectez-la via le QR code sur le dashboard avant de relancer ce script."
    }
    elseif ($_.Exception.InnerException -is [System.Net.Sockets.SocketException]) {
        Write-Host "Erreur reseau : impossible de joindre api.green-api.com." -ForegroundColor Red
        Write-Host "Verifiez votre connexion internet et reessayez."
    }
    else {
        Write-Host "Erreur inattendue : $_" -ForegroundColor Red
    }

    exit 1
}

$groups = @($contacts | Where-Object { $_.id -like "*@g.us" })

if ($groups.Count -eq 0) {
    Write-Host ""
    Write-Host "Aucun groupe WhatsApp trouve pour cette instance." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Assurez-vous que :"
    Write-Host "  1. L'instance est en ligne (statut Online sur le dashboard)"
    Write-Host "  2. Le numero lie est membre d'au moins un groupe WhatsApp"
    Write-Host "  3. L'instance a ete ajoutee comme participant dans chaque groupe"
    exit 0
}

Write-Host ""
Write-Host "$($groups.Count) groupe(s) trouve(s) :" -ForegroundColor Green
Write-Host ("-" * 55)

foreach ($group in $groups) {
    Write-Host ""
    Write-Host "  Nom : $($group.name)"
    Write-Host "  ID  : $($group.id)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ("-" * 55)
Write-Host "Bloc pret a coller dans votre fichier .env :" -ForegroundColor Cyan
Write-Host ""

foreach ($group in $groups) {
    $key = $group.name.ToUpper() -replace '[^A-Z0-9]', '_' -replace '_+', '_' -replace '^_|_$', ''
    Write-Host "WHATSAPP_GROUP_$key=$($group.id)"
}

Write-Host ""
Write-Host "Renommez les cles si necessaire pour correspondre aux valeurs 'target:' dans routing_rules.yaml." -ForegroundColor DarkGray
Write-Host ""
