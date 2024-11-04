# DBMove - MySQL Database Migration Tool

A GUI tool for easily migrating MySQL databases between servers. Built with Python and Tkinter, this tool provides a simple interface for database migration while handling common compatibility issues.

## Features

- User-friendly graphical interface
- Source and destination database connection testing
- Automatic handling of common MySQL compatibility issues:
  - DateTime/Timestamp default values
  - Character set and collation differences
  - Auto-increment values
- Session configuration saving (optional password storage)
- Progress feedback during migration
- Batch processing for large datasets

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dbmove
```

2. Install required dependencies:
```bash
pip install mysql-connector-python
```

## Usage

1. Run the application:
```bash
python main.py
```

2. In the GUI:
   - Fill in the source database connection details
   - Click "Test Connection" to verify source connection
   - Select the database you want to migrate
   - Fill in the destination database connection details
   - Click "Test Connection" to verify destination connection
   - Enter the new database name
   - Click "Start Migration" to begin the process

## Configuration

- Connection settings can be saved for future sessions
- Passwords can optionally be saved (using basic encoding)
- Last used database names are remembered

## Common Issues and Solutions

### Invalid Default Value Errors

The tool automatically handles common issues with datetime/timestamp default values:
- '0000-00-00 00:00:00' values are converted to NULL
- CURRENT_TIMESTAMP with ON UPDATE clauses are properly handled
- All datetime operations use UTC timezone to ensure consistency

### Access Denied Errors

If you encounter access denied errors:
1. Ensure the user has appropriate privileges on both source and destination servers
2. For some operations, SUPER privilege might be required
3. Verify the username and password are correct

### Character Set Issues

The tool automatically handles:
- Character set differences between servers
- Collation mismatches
- Encoding conversion issues

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
