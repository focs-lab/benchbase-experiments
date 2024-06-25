ALTER USER 'root'@'localhost' IDENTIFIED BY '1';
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost' WITH GRANT OPTION;
CREATE DATABASE benchbase;
