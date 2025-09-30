# Contributing to Privy Fraud Detection API

Thank you for your interest in contributing to Privy! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Ubuntu 22.04 LTS (recommended)
- Python 3.11+
- PostgreSQL 14+
- Redis 6+

### Development Setup
1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/privy.git`
3. Follow the [Ubuntu Setup Guide](UBUNTU_SETUP.md)
4. Create a virtual environment: `python3 -m venv .venv`
5. Install dependencies: `pip install -r requirements.txt`
6. Set up your `.env` file from `.env.template`

## 🛠 Development Workflow

### Before You Start
1. Create an issue to discuss your proposed changes
2. Fork the repository and create a feature branch
3. Set up your development environment

### Making Changes
1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Write tests**: Add tests for any new functionality
3. **Follow code style**: We use Python's PEP 8 standards
4. **Run tests**: `pytest tests/ -v`
5. **Test locally**: Start the API and verify your changes work

### Code Standards
- **Python Style**: Follow PEP 8
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Document all public functions and classes
- **Error Handling**: Proper exception handling with meaningful messages
- **Async/Await**: Use async patterns for I/O operations

### Commit Guidelines
```
type(scope): brief description

Detailed description of what changed and why.

- Bullet points for specific changes
- Reference issues: Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_scoring.py -v
```

### Writing Tests
- Write unit tests for new functions
- Add integration tests for API endpoints
- Mock external dependencies (Redis, PostgreSQL)
- Test edge cases and error conditions

## 📚 Areas for Contribution

### 🐛 Bug Reports
- Use the issue template
- Include steps to reproduce
- Provide environment details
- Include relevant logs

### ✨ Feature Requests
- Describe the use case
- Explain the expected behavior
- Consider backwards compatibility
- Discuss implementation approach

### 🎯 Good First Issues
- Documentation improvements
- Additional unit tests
- Code style improvements
- Small bug fixes

### 🚀 Advanced Contributions
- New fraud detection algorithms
- Performance optimizations
- Security improvements
- API endpoint additions

## 🔍 Code Review Process

1. **Submit PR**: Create a pull request with clear description
2. **Automated Checks**: Ensure all tests pass
3. **Code Review**: Maintainers will review your code
4. **Address Feedback**: Make requested changes
5. **Merge**: Once approved, your PR will be merged

## 📋 Pull Request Checklist

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated if needed
- [ ] Code follows project style guidelines
- [ ] Commit messages follow guidelines
- [ ] PR description explains changes clearly
- [ ] No merge conflicts

## 🏷 Release Process

We use semantic versioning (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

## 💬 Communication

- **Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion
- **Email**: For security issues (private disclosure)

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- Special thanks for major features

## ❓ Questions?

If you have questions about contributing:
1. Check existing issues and documentation
2. Create a discussion thread
3. Reach out to maintainers

Thank you for making Privy better! 🚀