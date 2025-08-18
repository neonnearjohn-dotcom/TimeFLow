param(
  [Parameter(Mandatory = $true)][string]$RepoUrl,
  [string]$Branch = "main",
  [string]$GitUserName = $env:GIT_USER_NAME,
  [string]$GitUserEmail = $env:GIT_USER_EMAIL
)

function Fail($msg) { Write-Error $msg; exit 1 }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Fail "Git не установлен. Установи Git и повтори."
}

# Настроим имя и email коммитов, если ещё не заданы
$existingEmail = git config user.email
if (-not $existingEmail) {
  if (-not $GitUserEmail) { $GitUserEmail = "you@example.com" }
  git config user.email $GitUserEmail | Out-Null
}
$existingName = git config user.name
if (-not $existingName) {
  if (-not $GitUserName) { $GitUserName = "Your Name" }
  git config user.name $GitUserName | Out-Null
}

# Инициализируем репозиторий и ветку
if (-not (Test-Path ".git")) { git init | Out-Null }

git rev-parse --verify $Branch 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { git checkout -b $Branch | Out-Null } else { git checkout $Branch | Out-Null }

# Базовый .gitignore (создаём, если его нет)
if (-not (Test-Path ".gitignore")) {
@"
node_modules/
.vscode/
.idea/
.DS_Store
*.log
.env
.env.*
venv/
.venv/
__pycache__/
dist/
build/
coverage/
.next/
out/
target/
*.pyc
*.pyo
*.pyd
*.swp
*.swo
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8 -NoNewline
}

# Готовим коммит
git add -A | Out-Null
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m "Initial upload" | Out-Null }

# origin  $RepoUrl
$remotes = git remote
if ($remotes -match '^origin$') {
  git remote set-url origin $RepoUrl | Out-Null
} else {
  git remote add origin $RepoUrl | Out-Null
}

# Пушим
git push -u origin $Branch
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Пуш не удался. Возможные причины:" -ForegroundColor Yellow
  Write-Host "1) Удалённая ветка уже существует с другой историей." -ForegroundColor Yellow
  Write-Host "   Если ты точно хочешь перезаписать удалённую ветку:" -ForegroundColor Yellow
  Write-Host "     git push --force-with-lease origin $Branch" -ForegroundColor Yellow
  Write-Host "2) Репозиторий не пустой (README и т.п.). Сделай pull/merge или используй форс-пуш." -ForegroundColor Yellow
  exit 1
}

Write-Host "Готово: отправлено в $RepoUrl (ветка $Branch)" -ForegroundColor Green
