USE cyberpunk_db;
CREATE TABLE courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO courses (name, description) VALUES
('Kubernetes для DevOps', 'Orchestration контейнеров и микросервисов'),
('Terraform Infrastructure as Code', 'Автоматизация облачной инфраструктуры'),
('CI/CD с Jenkins и GitLab CI', 'Автоматизация пайплайнов деплоя'),
('Мониторинг Prometheus + Grafana', 'Observability и алертинг'),
('Python FastAPI для DevOps', 'Создание REST API'),
('Distributed Systems', 'Масштабируемые архитектуры');

