# Project Agent Bootstrap

This directory is for local agent bootstrap only.

- `.agents/skills/gstack` should be a local link to the installed gstack checkout at `C:\Users\kira5\.gstack\repos\gstack`.
- Do not copy or vendor the full gstack skill tree into this repository.
- The durable project routing and safety rules live in `../AGENTS.md`.

If the link is missing, recreate it from PowerShell at the project root:

```powershell
New-Item -ItemType Directory -Force -Path .agents\skills
New-Item -ItemType Junction -Path .agents\skills\gstack -Target C:\Users\kira5\.gstack\repos\gstack
```

