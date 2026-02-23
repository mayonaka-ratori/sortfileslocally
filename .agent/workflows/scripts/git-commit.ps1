# Git Commit Automation

Write-Host "📦 Staging changes..." -ForegroundColor Cyan
git add .

$diff = git diff --cached --stat
if (-not $diff) {
    Write-Host "⚠️ No changes staged for commit." -ForegroundColor Yellow
    exit
}

Write-Host "📝 Generating commit message..." -ForegroundColor Cyan
# In a real assistant environment, the LLM would provide this.
# For the script, we'll use a placeholder or the first line of the diff stat.
$msg = "chore: Developer workflow and project structure optimizations"

Write-Host "💾 Committing..." -ForegroundColor Cyan
git commit -m $msg

Write-Host "🚀 Pushing..." -ForegroundColor Cyan
git push origin main
