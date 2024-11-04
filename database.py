import mysql.connector
from typing import List, Tuple, Optional
import re

class MySQLHandler:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def connect(self, host: str, port: int, user: str, password: str) -> Tuple[bool, str]:
        """
        Establish connection to MySQL server
        
        Args:
            host (str): Server hostname
            port (int): Server port
            user (str): Username
            password (str): Password
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            self.connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                sql_mode=''  # Disable strict mode at connection level
            )
            self.cursor = self.connection.cursor(buffered=True)
            # Only set session-level parameters
            self.cursor.execute("SET SESSION sql_mode=''")
            self.cursor.execute("SET SESSION time_zone='+00:00'")  # Ensure UTC timezone
            return True, "Connection successful"
        except mysql.connector.Error as err:
            return False, f"Error: {err}"

    def get_databases(self) -> List[str]:
        """
        Get list of databases from server
        
        Returns:
            List[str]: List of database names
        """
        if not self.cursor:
            return []
        
        self.cursor.execute("SHOW DATABASES")
        return [db[0] for db in self.cursor.fetchall()]

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def _modify_create_table_statement(self, create_stmt: str) -> str:
        """
        Modify create table statement to handle compatibility issues
        
        Args:
            create_stmt (str): Original CREATE TABLE statement
            
        Returns:
            str: Modified CREATE TABLE statement
        """
        # Remove DEFINER clause
        create_stmt = re.sub(r'DEFINER=`[^`]+`@`[^`]+`', '', create_stmt)
        
        # First, handle any datetime/timestamp columns with problematic defaults
        # This regex looks for column definitions that include datetime or timestamp
        datetime_cols = re.finditer(r'`(\w+)`\s+(datetime|timestamp)[^,\n]+', create_stmt, re.IGNORECASE)
        for match in datetime_cols:
            col_def = match.group(0)
            col_name = match.group(1)
            
            # If it has a default value of zeros or invalid date
            if "'0000-00-00" in col_def or "'0000-00-00 00:00:00'" in col_def:
                new_def = f"`{col_name}` {match.group(2)} DEFAULT NULL"
                create_stmt = create_stmt.replace(col_def, new_def)
            # If it has CURRENT_TIMESTAMP with ON UPDATE
            elif "CURRENT_TIMESTAMP" in col_def and "ON UPDATE" in col_def:
                new_def = f"`{col_name}` {match.group(2)} DEFAULT CURRENT_TIMESTAMP"
                create_stmt = create_stmt.replace(col_def, new_def)
        
        # Handle other problematic patterns
        replacements = [
            (r"DEFAULT '0000-00-00 00:00:00'", "DEFAULT NULL"),
            (r"DEFAULT '0000-00-00'", "DEFAULT NULL"),
            (r"DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP", "DEFAULT CURRENT_TIMESTAMP"),
            (r"ON UPDATE CURRENT_TIMESTAMP", ""),
            (r"CHARACTER SET [a-zA-Z0-9_]+ ", ""),
            (r"COLLATE [a-zA-Z0-9_]+ ", ""),
            (r"DEFAULT b'0'", "DEFAULT 0"),
            (r"DEFAULT b'1'", "DEFAULT 1"),
        ]
        
        for pattern, replacement in replacements:
            create_stmt = re.sub(pattern, replacement, create_stmt)
        
        # Remove auto increment if present (will be added back by MySQL)
        create_stmt = re.sub(r'AUTO_INCREMENT=\d+ ', '', create_stmt)
        
        return create_stmt

    def _get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            List[str]: List of column names
        """
        self.cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        return [column[0] for column in self.cursor.fetchall()]

    def migrate_database(self, source_db: str, dest_handler: 'MySQLHandler', dest_db: str) -> Tuple[bool, str]:
        """
        Migrate database from source to destination
        
        Args:
            source_db (str): Source database name
            dest_handler (MySQLHandler): Destination connection handler
            dest_db (str): Destination database name
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            # Set only session-level parameters
            self.cursor.execute("SET SESSION sql_mode=''")
            self.cursor.execute("SET SESSION time_zone='+00:00'")  # Ensure UTC timezone
            dest_handler.cursor.execute("SET SESSION sql_mode=''")
            dest_handler.cursor.execute("SET SESSION time_zone='+00:00'")  # Ensure UTC timezone
            
            # Create destination database
            dest_handler.cursor.execute(f"DROP DATABASE IF EXISTS {dest_db}")
            dest_handler.cursor.execute(f"CREATE DATABASE {dest_db}")
            
            # Get all tables from source
            self.cursor.execute(f"USE {source_db}")
            self.cursor.execute("SHOW TABLES")
            tables = self.cursor.fetchall()
            
            total_tables = len(tables)
            for index, table in enumerate(tables, 1):
                table_name = table[0]
                
                # Get create table statement
                self.cursor.execute(f"SHOW CREATE TABLE {table_name}")
                create_stmt = self.cursor.fetchone()[1]
                
                # Modify create statement for compatibility
                create_stmt = self._modify_create_table_statement(create_stmt)
                
                # Create table in destination
                dest_handler.cursor.execute(f"USE {dest_db}")
                try:
                    dest_handler.cursor.execute(create_stmt)
                except mysql.connector.Error as err:
                    if err.errno == 1050:  # Table already exists
                        pass
                    else:
                        raise
                
                # Copy data
                self.cursor.execute(f"SELECT * FROM {table_name}")
                rows = self.cursor.fetchall()
                
                if rows:
                    # Get column names
                    columns = self._get_table_columns(table_name)
                    placeholders = ', '.join(['%s'] * len(columns))
                    
                    # Insert in batches of 1000
                    batch_size = 1000
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                        dest_handler.cursor.executemany(insert_query, batch)
                        dest_handler.connection.commit()
            
            return True, f"Migration completed successfully. Migrated {total_tables} tables."
            
        except mysql.connector.Error as err:
            error_msg = str(err)
            if "1067" in error_msg:  # Invalid default value
                return False, f"Migration failed: Invalid default value detected. Error: {error_msg}"
            elif "1146" in error_msg:  # Table doesn't exist
                return False, f"Migration failed: Table not found. Error: {error_msg}"
            elif "1045" in error_msg:  # Access denied
                return False, f"Migration failed: Access denied. Please check permissions. Error: {error_msg}"
            elif "1227" in error_msg:  # Access denied (SUPER privilege)
                return False, f"Migration failed: This operation requires elevated privileges. Please use a user with appropriate permissions. Error: {error_msg}"
            else:
                return False, f"Migration failed: {error_msg}"
        except Exception as e:
            return False, f"Migration failed: Unexpected error: {str(e)}"
