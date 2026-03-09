-- Create a new database
CREATE DATABASE IF NOT EXISTS mydatabase;
-- Grant privileges to a user (if needed)
GRANT ALL PRIVILEGES ON mydatabase.* TO 'saad' @'%' IDENTIFIED BY 'saad';
-- Flush privileges to apply the changes
FLUSH PRIVILEGES;