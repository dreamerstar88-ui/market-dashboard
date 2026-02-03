---
description: GitHub Desktop을 통해 변경사항을 커밋하고 푸시하는 방법
---

# GitHub Desktop Push Skill

## 개요
이 프로젝트에서 GitHub에 변경사항을 푸시하려면 GitHub Desktop에 포함된 Git을 사용해야 합니다.

## Git 실행 파일 경로
```
C:\Users\PSJ_1\AppData\Local\GitHubDesktop\app-3.5.4\resources\app\git\cmd\git.exe
```

> **참고**: GitHub Desktop 업데이트 시 버전 번호(app-3.5.4)가 변경될 수 있습니다.
> 경로를 찾으려면: `Get-ChildItem -Path "$env:LOCALAPPDATA" -Filter "git.exe" -Recurse -Depth 6 | Select-Object -First 1`

## 사용법

### 1. 변경사항 스테이징
```powershell
// turbo
& "C:\Users\PSJ_1\AppData\Local\GitHubDesktop\app-3.5.4\resources\app\git\cmd\git.exe" add -A
```

### 2. 커밋
```powershell
& "C:\Users\PSJ_1\AppData\Local\GitHubDesktop\app-3.5.4\resources\app\git\cmd\git.exe" commit -m "커밋 메시지"
```

### 3. 푸시
```powershell
& "C:\Users\PSJ_1\AppData\Local\GitHubDesktop\app-3.5.4\resources\app\git\cmd\git.exe" push
```

## 버전 확인
```powershell
// turbo
& "C:\Users\PSJ_1\AppData\Local\GitHubDesktop\app-3.5.4\resources\app\git\cmd\git.exe" --version
```

## 주의사항
- 일반 `git` 명령어는 PowerShell PATH에 등록되어 있지 않으므로 전체 경로 사용 필수
- GitHub Desktop 업데이트 후 경로가 변경될 수 있음
