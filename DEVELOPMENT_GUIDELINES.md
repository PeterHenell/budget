# Development Guidelines & Prompt Instructions

## 🎯 **GENERAL DEVELOPMENT PRINCIPLES**

### **Code Quality Standards**
1. **Fail Fast Principle**: Code should assume latest database schema and fail immediately if expectations aren't met
2. **No Backwards Compatibility**: Don't add complex compatibility layers - require proper migrations
3. **Structured Logging**: Always use the logging framework (`from logging_config import get_logger`) - never `print()`
4. **Type Hints**: Include type hints for all function parameters and return values
5. **Error Handling**: Use proper exception handling with meaningful error messages
6. **Documentation**: Include docstrings for all public methods and complex logic

### **Architecture Guidelines**
1. **Dependency Injection**: Avoid global variables - use dependency injection patterns
2. **Single Responsibility**: Each method should have one clear purpose
3. **Method Length**: Keep methods under 30 lines - break down complex operations
4. **Database Efficiency**: Use indexed lookups, avoid O(n) operations, prefer direct queries
5. **Thread Safety**: Consider concurrent access when designing shared resources

### **Security Requirements**
1. **No Default Passwords**: Never allow default/empty passwords in any user creation
2. **Input Validation**: Validate all user inputs before database operations
3. **SQL Injection Prevention**: Always use parameterized queries
4. **Authentication**: Require proper authentication for all sensitive operations
5. **Role-Based Access**: Implement proper role checking for admin functions

---

## 🛠️ **SPECIFIC PROJECT INSTRUCTIONS**

### **Database Operations**
- **Schema Assumptions**: Always assume latest database schema - don't check for column existence
- **Connection Management**: Use the established connection patterns in `BudgetDb` class  
- **Indexing**: Ensure efficient queries using existing indexes (transactions by verification number, date, category)
- **Error Messages**: Database errors should be descriptive and logged properly

### **Classification System**
- **LLM Priority**: Classification system prioritizes LLM classifiers when available
- **Confidence Tracking**: Always include confidence scores and classification methods
- **Fallback Strategy**: Graceful degradation from LLM → rule-based → manual classification
- **Performance**: Classification operations should be efficient and not block the UI

### **Web Application**
- **Thread Safety**: Use `get_logic()` function instead of global variables
- **Error Handling**: Provide user-friendly error messages via flash messages
- **API Consistency**: All API endpoints should return JSON with consistent error/success format
- **Authentication**: All routes (except login) should require authentication

### **Testing Requirements**
- **Run Tests Regularly**: Execute tests after any significant changes
- **Integration Tests**: Test database operations with actual database connections
- **Error Scenarios**: Test error conditions and edge cases
- **Performance**: Verify that optimizations actually improve performance

---

## 📋 **CODE REVIEW CHECKLIST**

Before any code changes, verify:

- [ ] **Logging**: No `print()` statements - use proper logging
- [ ] **Error Handling**: Proper exception handling with meaningful messages  
- [ ] **Type Hints**: Function signatures include type information
- [ ] **Documentation**: Public methods have docstrings
- [ ] **Security**: No hardcoded passwords or insecure defaults
- [ ] **Performance**: No O(n) operations where O(1) is possible
- [ ] **Database**: Proper parameterized queries, no SQL injection risks
- [ ] **Testing**: Changes don't break existing functionality

---

## 🚨 **ANTI-PATTERNS TO AVOID**

### **Never Do These:**
1. **`print()` for logging** → Use `self.logger.info()` etc.
2. **Global variables** → Use dependency injection or app context
3. **Default passwords** → Always require secure password parameters
4. **Backwards compatibility checks** → Assume latest schema, fail fast
5. **Long methods (50+ lines)** → Break into smaller, focused functions
6. **Hardcoded configuration** → Use environment variables or config files
7. **Silent failures** → Log errors and provide clear user feedback
8. **SQL string concatenation** → Use parameterized queries only

### **Performance Anti-Patterns:**
1. **Loading all records to find one** → Use indexed lookups
2. **N+1 database queries** → Use joins or batch operations
3. **Unnecessary compatibility checks** → Trust the schema is current
4. **Inefficient loops** → Use database operations where possible

---

## 🎯 **PROMPT TEMPLATE**

When making changes, always include:

```
Context: [Brief description of what you're working on]
Requirements: [Specific requirements or constraints]  
Quality Checks:
- [ ] Uses logging framework instead of print()
- [ ] Includes proper error handling
- [ ] Follows fail-fast principle for database schema
- [ ] No security vulnerabilities (passwords, SQL injection)
- [ ] Performance considerations addressed
- [ ] Tests run successfully after changes

Guidelines Applied:
- Database: [Latest schema assumed, efficient queries]
- Security: [No defaults, proper validation]
- Architecture: [Dependency injection, single responsibility]
- Testing: [Integration tests run, functionality verified]
```

---

## 📚 **REFERENCE DOCUMENTATION**

- **Database Schema**: Assume all confidence tracking and classification columns exist
- **Logging**: Use `logging_config.py` - structured logging with levels
- **Classification**: See `src/classifiers/` module documentation  
- **API Patterns**: Follow established patterns in `web_app.py`
- **Security**: Reference user management functions in `BudgetDb` class

---

**Last Updated**: August 23, 2025  
**Project**: Budget Management Application  
**Status**: Active Development Guidelines
