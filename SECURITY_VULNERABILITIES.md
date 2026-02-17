# Security Vulnerabilities Report

**Generated**: 2026-02-15  
**Total Vulnerabilities Found**: 15 known vulnerabilities in 7 packages  
**Severity**: 20 High, 9 Moderate, 1 Low (from GitHub Dependabot)

---

## 🔴 Critical Findings

### 1. MLflow (2.18.0) - 8 Vulnerabilities

**Current Version**: 2.18.0  
**Recommended Action**: Upgrade to 2.22.4 or higher (preferably 3.5.0+)

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2025-14279 | High | DNS rebinding attack vulnerability - missing Origin header validation in REST server | 3.5.0 |
| CVE-2025-11201 | High | Security vulnerability requiring patch | 2.22.4 or 3.0.0 |
| CVE-2025-11200 | High | Security vulnerability | 2.22.0rc0 |
| CVE-2025-1473 | High | Security vulnerability | 2.20.3 |
| CVE-2025-10279 | High | Security vulnerability | 3.4.0rc0 |
| PYSEC-2025-52 | High | Security advisory | 3.1.0 |
| PYSEC-2025-17 | High | Admin accounts can be created without passwords | 2.19.0 |
| CVE-2024-37059 | Moderate | GraphQL DoS via uncontrolled resource consumption | No fix listed |

**Additional Known Issues**:
- **MLflow 2.17.x**: GraphQL endpoint vulnerable to DoS through large batch queries
- **MLflow 2.17.0-2.20.1**: CSRF vulnerability in signup feature
- **MLflow 2.15.1**: Path traversal vulnerability in DBFS service
- **MLflow 2.13.2**: DoS vulnerability from unlimited experiment name length

### 2. Werkzeug (3.1.3) - 2 Vulnerabilities

**Current Version**: 3.1.3  
**Recommended Action**: Upgrade to 3.1.5 or higher

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2026-21860 | High | Windows device name handling with extensions/trailing spaces | 3.1.5 |
| CVE-2025-66221 | High | Windows device name vulnerability in safe_join() | 3.1.4 |

**Additional Known Issues**:
- **CVE-2024-34069**: Werkzeug debugger allows code execution (fixed in 3.0.3)
- **CVE-2024-49767**: MultiPartParser vulnerability (fixed in 3.0.6)

### 3. Pillow (11.0.0) - 1 Vulnerability

**Current Version**: 11.0.0  
**Recommended Action**: Upgrade to 12.1.1

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2026-25990 | High | Image processing vulnerability | 12.1.1 |

### 4. Cryptography (46.0.3) - 1 Vulnerability

**Current Version**: 46.0.3  
**Recommended Action**: Upgrade to 46.0.5

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2026-26007 | Moderate | Cryptographic vulnerability | 46.0.5 |

### 5. urllib3 (2.6.2) - 1 Vulnerability

**Current Version**: 2.6.2  
**Recommended Action**: Upgrade to 2.6.3

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2026-21441 | Moderate | HTTP client vulnerability | 2.6.3 |

### 6. pyasn1 (0.6.1) - 1 Vulnerability

**Current Version**: 0.6.1  
**Recommended Action**: Upgrade to 0.6.2

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2026-23490 | Low | ASN.1 parsing vulnerability | 0.6.2 |

### 7. pip (25.3) - 1 Vulnerability

**Current Version**: 25.3  
**Recommended Action**: Upgrade to 26.0 or higher

| CVE ID | Severity | Description | Fix Version |
|--------|----------|-------------|-------------|
| CVE-2026-1703 | Low | Package installer vulnerability | 26.0 |

---

## 📊 Risk Assessment

### High Priority (Fix Before Production)
1. ✅ **MLflow** - Multiple high-severity vulnerabilities including DNS rebinding, CSRF, and path traversal
2. ✅ **Werkzeug** - Windows-specific vulnerabilities (less critical if running on Linux/Docker)
3. ✅ **Pillow** - Image processing vulnerabilities

### Medium Priority (Fix Soon)
4. ⚠️ **Cryptography** - Used by MLflow and other packages for encryption
5. ⚠️ **urllib3** - HTTP client library used throughout

### Low Priority (Monitor)
6. ℹ️ **pyasn1** - ASN.1 parser, low severity
7. ℹ️ **pip** - Development tool, not deployed

---

## 🛠️ Recommended Actions

### Immediate (Before Certification Demo)

**Option 1: Quick Security Patch** (Recommended for demo)
```bash
# Only update the most critical packages
pip install --upgrade mlflow==2.22.4 pillow==12.1.1 cryptography==46.0.5 urllib3==2.6.3 werkzeug==3.1.5
```

**Option 2: Full Update** (More thorough but may require testing)
```bash
# Update all vulnerable packages
pip install --upgrade mlflow pillow cryptography urllib3 werkzeug pyasn1 pip
```

### After Certification

1. **Test thoroughly** - Run your full test suite after updates
2. **Update requirements files** - Pin new versions in all requirements*.txt
3. **Verify MLflow compatibility** - Test experiment tracking and model loading
4. **Check Streamlit UI** - Ensure all pages work correctly
5. **Test API endpoints** - Verify predictions still work

---

## 🔍 Detailed Analysis by Package

### MLflow Security Issues

**Why so many vulnerabilities?**
- MLflow is a complex web application with multiple endpoints
- Includes UI components, REST API, and artifact storage
- Version 2.18.0 is several releases behind (current stable: 3.5.0+)

**Impact on your project**:
- ✅ **Low risk for demo**: You're running locally, not exposed to internet
- ❌ **High risk for production**: Would be vulnerable if deployed publicly
- ⚠️ **Admin account creation**: Could allow unauthorized access
- ⚠️ **Path traversal**: Could expose sensitive files
- ⚠️ **CSRF**: Could allow unauthorized actions

**Recommended upgrade path**:
1. Test with MLflow 2.22.4 first (maintains 2.x compatibility)
2. If all works well, consider upgrading to 3.5.0 for latest security

### Werkzeug Issues

**Windows-specific vulnerabilities**:
- Most Werkzeug CVEs affect Windows deployments
- Less critical if you're running in Docker on Linux
- Still recommended to update for defense-in-depth

**Impact**: Low if running in Linux containers (which you are)

### Pillow Vulnerability

**Image processing risk**:
- Pillow 11.0.0 has known vulnerabilities in image parsing
- Could be exploited via malicious product images
- Recommended to upgrade to 12.1.1

**Impact**: Medium - You process product images in your pipeline

---

## 📝 SQLAlchemy Status

**Current Version**: 1.4.50  
**Status**: ✅ **No known vulnerabilities**

SQLAlchemy 1.4.50 has a safety score of 100 with no documented CVEs in 2024-2025. The latest 1.4.x releases (1.4.53, 1.4.54) include backported security fixes, but 1.4.50 itself is secure.

**Note**: You might want to upgrade to 1.4.54 for latest patches, but it's not critical.

---

## 🚀 Quick Fix Script

Create a file `fix_vulnerabilities.sh`:

```bash
#!/bin/bash
# Security vulnerability fix script

echo "🔒 Updating vulnerable packages..."

# Activate virtual environment
source .venv/bin/activate

# Update pip first
pip install --upgrade pip==26.0.1

# Update vulnerable packages
pip install --upgrade \
    mlflow==2.22.4 \
    pillow==12.1.1 \
    cryptography==46.0.5 \
    urllib3==2.6.3 \
    werkzeug==3.1.5 \
    pyasn1==0.6.2

# Update requirements files
pip freeze > requirements.txt

echo "✅ Security updates complete!"
echo "🧪 Please test your application:"
echo "  1. make start"
echo "  2. make run-streamlit"
echo "  3. Test training and predictions"
```

Run with:
```bash
chmod +x fix_vulnerabilities.sh
./fix_vulnerabilities.sh
```

---

## ⚠️ Important Notes

### For Your Certification Demo

**Do NOT update before your demo** unless you have time to test everything thoroughly. The vulnerabilities are:
- Low risk in a local development environment
- Not exploitable without network access
- Unlikely to affect your demo functionality

**After certification**, update immediately before deploying to any shared or production environment.

### Testing After Updates

Required tests:
1. ✅ MLflow tracking - Log a test experiment
2. ✅ Model training - Train and register a model
3. ✅ API predictions - Test the /predict endpoint
4. ✅ Streamlit UI - Check all 4 pages work
5. ✅ MinIO artifacts - Verify artifact upload/download
6. ✅ Database connections - Ensure PostgreSQL connectivity

### GitHub Dependabot Alerts

GitHub reported 30 vulnerabilities total:
- 20 High severity
- 9 Moderate severity
- 1 Low severity

The pip-audit found 15 direct vulnerabilities. The difference (15 more) likely comes from:
- Transitive dependencies (packages required by your packages)
- GitHub's more aggressive vulnerability detection
- Development dependencies in virtual environment

---

## 📚 References

- [MLflow Security Advisories](https://advisories.gitlab.com/pkg/pypi/mlflow/)
- [Python Advisory Database](https://github.com/pypa/advisory-database)
- [Werkzeug CVE List](https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword=Werkzeug)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)

---

## ✅ Action Checklist

**Before Certification** (Optional):
- [ ] Review this report
- [ ] Decide if updates are needed (probably not)
- [ ] Document known vulnerabilities for Q&A

**After Certification** (Required):
- [ ] Run `fix_vulnerabilities.sh` script
- [ ] Update all requirements*.txt files
- [ ] Test all functionality
- [ ] Run pip-audit again to verify fixes
- [ ] Rebuild Docker images with updated dependencies
- [ ] Commit and push security updates

---

**Last Updated**: 2026-02-15  
**Next Review**: After certification demo
