# Contributing to MemDB

First off, thank you for considering contributing to MemDB! It's people like you that make MemDB such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to <shaikh.adnan.dev@gmail.com>.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title** for the issue
- **Describe the exact steps which reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include screenshots and animated GIFs if possible**
- **Include your environment details** (OS, Python version, PostgreSQL version)
- **Include any relevant logs and error messages**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title** for the issue
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and the expected behavior**
- **Explain why this enhancement would be useful to most MemDB users**

### Pull Requests

- Fill in the required template
- Follow the Python styleguides
- Include appropriate test cases
- Update documentation as needed
- End all files with a newline

## Development Setup

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Git

### Getting Started

1. **Fork the repository**

   ```bash
   git clone https://github.com/yourusername/memdb.git
   cd memdb
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up PostgreSQL for testing**

   ```bash
   # Using Docker
   docker-compose up -d postgres
   
   # Create test database
   createdb -h localhost -U memdb_user -d memdb_test
   ```

5. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dyn_memdb tests/

# Run specific test file
pytest tests/test_memdb.py

# Run with verbose output
pytest -v

# Run with asyncio debugging
pytest -vv -s
```

### Code Style

We follow PEP 8 style guidelines. Please ensure your code adheres to these standards:

```bash
# Format code with black
black dyn_memdb/ tests/

# Check with flake8
flake8 dyn_memdb/ tests/

# Type checking with mypy
mypy dyn_memdb/
```

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  - 🎨 `:art:` - Improve structure/format
  - 🐛 `:bug:` - Fix a bug
  - ✨ `:sparkles:` - Introduce new features
  - 📚 `:books:` - Documentation
  - ⚡ `:zap:` - Improve performance
  - ✅ `:white_check_mark:` - Add tests
  - 🔒 `:lock:` - Security fix
  - 🚀 `:rocket:` - Release/deployment

Example:

```
🎨 Refactor cache eviction logic for better readability

- Simplified the eviction algorithm
- Added comprehensive comments
- Improved performance by 15%

Fixes #123
```

## Documentation

- Update README.md if you change behavior
- Add docstrings to all functions and classes
- Use type hints in your code
- Include examples for new features

### Documentation Style

```python
def insert(self, table_name: str, key: str, record: dict) -> None:
    """
    Insert a record into the memory cache.
    
    Records are stored in memory first and flushed to PostgreSQL
    at configured intervals. Inserting a record with an existing
    key updates the record.
    
    Args:
        table_name: Name of the table to insert into
        key: Unique identifier for the record
        record: Dictionary containing the record data
        
    Returns:
        None
        
    Raises:
        ValueError: If table_name or key is empty
        TypeError: If record is not a dictionary
        
    Example:
        >>> await db.insert("users", "user_123", {"name": "John", "age": 30})
    """
    pass
```

## Pull Request Process

1. Update the CHANGELOG.md with notes on your changes
2. Update the README.md with any new documentation
3. Ensure all tests pass: `pytest`
4. Ensure code style compliance: `black` and `flake8`
5. Add tests for any new functionality
6. Push to your fork and open a pull request

## Additional Notes

### Issue and Pull Request Labels

This section lists the labels we use to help organize and categorize issues and pull requests.

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `performance` - Performance improvements
- `testing` - Tests or testing infrastructure
- `security` - Security-related issues
- `help-wanted` - Extra attention is needed
- `good-first-issue` - Good for newcomers

## Recognition

Contributors will be recognized in:

- The README.md file
- CHANGELOG.md for significant contributions
- GitHub contributors page

## Questions?

Feel free to contact the maintainer at <shaikh.adnan.dev@gmail.com> or create an issue with the `question` label.

---

Thank you for contributing! 🎉
