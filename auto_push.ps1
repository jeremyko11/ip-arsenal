# IP Arsenal Auto Push Script
# 自动添加所有更改、提交并推送到 GitHub

$repoPath = "C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal"
$gitEmail = "auto-push@ip-arsenal.local"
$gitName = "Auto Push"

Set-Location $repoPath

# 设置 git 用户（如果尚未设置）
git config user.email $gitEmail
git config user.name $gitName

# 检查是否有更改
$status = git status --porcelain

if ($status) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    git add -A
    git commit -m "Auto sync - $timestamp"
    git push -u origin master
    Write-Host "[$timestamp] Changes pushed successfully"
} else {
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - No changes to push"
}
