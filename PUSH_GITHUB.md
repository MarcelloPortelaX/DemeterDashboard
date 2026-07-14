# Publicar as alterações no GitHub

Abra o terminal dentro desta pasta e execute:

```powershell
git status
git add .
git commit -m "Revisa textos e adiciona distribuição portátil para Windows"
git branch -M main
git remote -v
git push origin main
```

Se esta pasta ainda não estiver ligada ao repositório:

```powershell
git init
git add .
git commit -m "Revisa textos e adiciona distribuição portátil para Windows"
git branch -M main
git remote add origin https://github.com/MarcelloPortelaX/demeter-dashboard.git
git push -u origin main
```

Se o GitHub recusar porque o repositório remoto possui commits que não estão na pasta local:

```powershell
git pull origin main --rebase
git push origin main
```

Depois do push, para gerar o executável portátil, abra a aba **Actions**, selecione **Gerar executável Windows** e execute **Run workflow**. Ao terminar, baixe o artefato `DemeterDashboard-Windows`.
