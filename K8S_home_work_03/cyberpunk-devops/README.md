# 🚀 Cyberpunk DevOps API

Неоновое веб-приложение в стиле Cyberpunk 2077 с REST API для демонстрации DevOps навыков. Статическая главная страница + динамические API эндпоинты с MariaDB.

## ✨ Функционал

- **/health** - Health check с информацией об ОС `{"server": "Linux", "status": "OK"}`
- **/** - Главная страница в cyberpunk стиле с информацией об авторе
- **/courses** - Список IT курсов из MariaDB (fallback JSON при ошибке БД)
- **/docs** - Автогенерируемая Swagger документация FastAPI

## 🛠 Технологический стек
- Frontend: HTML5 + Cyberpunk CSS + Orbitron/VT323 шрифты
- Backend: Python 3.10+ FastAPI + Uvicorn
- Database: MariaDB 10.6+
- Web Server: Nginx 1.18+

## ⚙ Конфигурация

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DB_HOST` | localhost | Хост MariaDB |
| `DB_USER` | cyberpunk | Пользователь БД |
| `DB_PASSWORD` | SecurePass2025! | Пароль БД |
| `DB_NAME` | cyberpunk_db | Имя базы |






# Cyberpunk DevOps — деплой в Kubernetes

Развёртывание приложения [cyberpunk-devops](https://github.com/AnastasiyaGapochkina01/cyberpunk-devops) (FastAPI-бэкенд + MariaDB) в Kubernetes.

## Структура проекта

```
.
├── Dockerfile                        # сборка образа бэкенда (api/ + static/)
├── .gitignore
├── README.md
└── k8s/
    ├── 00-namespace.yaml             # namespace "cyberpunk"
    ├── 01-secret-db.yaml             # Secret с доступами к БД
    ├── 02-configmap-db-init.yaml     # init.sql для MariaDB (схема + seed-данные)
    ├── 03-mariadb-statefulset.yaml   # headless Service + StatefulSet + PVC 1Gi (RWO)
    └── 04-backend-deployment.yaml    # Deployment (3 реплики, liveness/readiness) + Service
```

## Требования к окружению

- Kubernetes-кластер (minikube / kind / k3s / managed EKS-GKE-AKS)
- `kubectl` настроен на нужный контекст
- Docker для сборки образа
- Доступ к container registry (Docker Hub, GHCR, private registry)
- Рекомендуемый размер узла: **2 vCPU / 4 GiB RAM** (managed worker node) или **4 vCPU / 8 GiB RAM** (all-in-one кластер, где control plane и workload на одном узле)

## Шаг 1. Собрать и запушить образ бэкенда

```bash
git clone https://github.com/AnastasiyaGapochkina01/cyberpunk-devops
cd cyberpunk-devops

# скопировать Dockerfile из этого проекта в корень репозитория
cp /path/to/this/project/Dockerfile .

docker build -t your-registry/cyberpunk-backend:1.0 .
docker push your-registry/cyberpunk-backend:1.0
```

Затем поправить `image:` в `k8s/04-backend-deployment.yaml` на реальный путь к образу.

## Шаг 2. Настроить секрет с доступами к БД

По умолчанию в `k8s/01-secret-db.yaml` лежат тестовые пароли. Для реального окружения рекомендуется создавать Secret императивно, не коммитя пароли в git:

```bash
kubectl create namespace cyberpunk

kubectl create secret generic db-credentials -n cyberpunk \
  --from-literal=DB_HOST=mariadb \
  --from-literal=DB_USER=cyberpunk \
  --from-literal=DB_PASSWORD='SecurePass2025!' \
  --from-literal=DB_NAME=cyberpunk_db \
  --from-literal=MYSQL_ROOT_PASSWORD='RootSecurePass2025!'
```

Если используете файл `01-secret-db.yaml` — просто поменяйте значения перед применением.

## Шаг 3. Применить манифесты

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-secret-db.yaml
kubectl apply -f k8s/02-configmap-db-init.yaml
kubectl apply -f k8s/03-mariadb-statefulset.yaml
kubectl apply -f k8s/04-backend-deployment.yaml
```

Или всё сразу (kubectl применит файлы в алфавитном порядке имён, поэтому порядок сохранится):

```bash
kubectl apply -f k8s/
```

## Проверка

```bash
kubectl get all -n cyberpunk
kubectl get pvc -n cyberpunk
kubectl get pods -n cyberpunk -w        # дождаться, пока все поды Running

# проброс порта, чтобы открыть приложение локально
kubectl port-forward -n cyberpunk svc/cyberpunk-backend 8080:80
# после этого приложение доступно на http://localhost:8080
```

Проверка liveness-эндпоинта:

```bash
kubectl exec -n cyberpunk deploy/cyberpunk-backend -- curl -s localhost:8000/health
```

## Как выполнены требования задания

1. **Бэкенд в 3 репликах** — `Deployment cyberpunk-backend`, `spec.replicas: 3`.
2. **Liveness-проба бэкенда** — `httpGet` на `/health:8000` (реальный эндпоинт из `api/main.py`). Дополнительно добавлена readiness-проба.
3. **БД через StatefulSet с PVC** — `mariadb:10.6`, `volumeClaimTemplates` на **1Gi**, режим доступа **ReadWriteOnce**, плюс headless Service `mariadb` для стабильного DNS-имени пода.
4. **Доступы к БД из Secret** — `Secret db-credentials`; бэкенд получает переменные через `envFrom.secretRef`, StatefulSet MariaDB — через `secretKeyRef` (root-пароль, база, пользователь, пароль).

## Важные замечания

- Пароли в `01-secret-db.yaml` — тестовые, для production использовать внешние секрет-хранилища (Vault, Sealed Secrets, SOPS) или создавать секрет императивно (см. Шаг 2).
- ConfigMap `02-configmap-db-init.yaml` содержит init-SQL, воссоздающий таблицу `courses` с тем же набором данных, что используется как fallback в `main.py`. Если в репозитории появится собственный `db_scripts/*.sql`, замените содержимое ConfigMap на него.
- Ресурсы (`resources.requests/limits`) заданы только для бэкенда; для StatefulSet MariaDB рекомендуется тоже прописать лимиты под нагрузку вашего окружения.







1  sudo apt updte
    2  sudo apt update
    3  sudo apt upgrade
    4  mkdir pr
    5  cd pr/
    6  git clone https://github.com/vaiz1982/K8S_home_work_03.git
    7  ls
    8  cd K8S_home_work_03/
    9  ls
   10  cd cyberpunk-devops/
   11  ls
   12  cd ..
   13  ls
   14  rm -rf K8S_home_work_03/
   15  ls
   16  git clone https://github.com/anestesia001/cyberpunk-devops.git
   17  ls
   18  cd cyberpunk-devops/
   19  ls
   20  cat README.md 
   21  clear
   22  ls
   23  pwd
   24  nano Dockerfile
   25  sudo nano install tree
   26  sudo apt install tree
   27  clear
   28  gree
   29  tree
   30  clear
   31  mkdir k8s
   32  cd k8s/
   33  sudo nano 00_namespace.yaml
   34  sudo nano 01_secretDB.yaml
   35  sudo nano 02_configMapDBinit.yaml
   36  sudo nano 03_mariaDBstateFullSet.yaml
   37  sudo nano 04_backEndDeployment.yaml
   38  sudo nano k8s-setup.sh
   39  sudo apt update && sudo apt upgrade
   40  ls -lah
   41  chmod +x k8s-setup.sh 
   42  sudo chmod +x k8s-setup.sh 
   43  sudo NODE_ROLE=master ./k8s-setup.sh
   44  ls
   45  ls -lah
   46  nano 00_namespace.yaml 
   47  nano 01_secretDB.yaml 
   48  nano 02_configMapDBinit.yaml 
   49  nano 03_mariaDBstateFullSet.yaml 
   50  nano 04_backEndDeployment.yaml 
   51  sudo nano 04_backEndDeployment.yaml 
   52  kubectl apply -f 00_namespace.yaml 
   53  kubectl apply -f 01_secretDB.yaml 
   54  kubectl apply -f 02_configMapDBinit.yaml 
   55  kubectl apply -f 03_mariaDBstateFullSet.yaml 
   56  kubectl apply -f 04_backEndDeployment.yaml 
   57  kubectl get deploy
   58  nano 00_namespace.yaml 
   59  kubectl -n cyberpunk get deploy
   60  df -h
   61  cd ..
   62  ls
   63  cd ..
   64  ls
   65  cd ..
   66  ls
   67  mv pr K8S_home_work_03 
   68  ls
   69  git init
   70  git status
   71  ls
   72  sudo nano .gitignore
   73  git status
   74  ls
   75  cd K8S_home_work_03/
   76  ls
   77  ls -lah
   78  cd cyberpunk-devops/
   79  ls
   80  ls -lah
   81  cat .gitignore 
   82  ls
   83  sudo nano README.md 
   84  history
