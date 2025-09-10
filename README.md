# DNS Manager

## Overview

DNS Manager is a powerful and user-friendly Python application designed to simplify DNS record management across multiple DNS providers. This tool provides a unified interface for managing DNS records, making it easier for system administrators, developers, and IT professionals to handle their domain configurations efficiently.

## Features

### Core Functionality
- **Multi-Provider Support**: Compatible with major DNS providers including:
  - Cloudflare
  - AWS Route 53
  - Google Cloud DNS
  - DigitalOcean DNS
  - Namecheap
  - And more...

### DNS Record Management
- **Create**: Add new DNS records with validation
- **Read**: View and search existing DNS records
- **Update**: Modify existing DNS records safely
- **Delete**: Remove DNS records with confirmation prompts

### Advanced Features
- **Bulk Operations**: Manage multiple records simultaneously
- **Backup & Restore**: Create backups of DNS configurations
- **Zone File Import/Export**: Support for standard zone file formats
- **Real-time Validation**: Validate DNS records before applying changes
- **Change History**: Track all DNS modifications with timestamps
- **TTL Management**: Flexible Time-To-Live configuration

### Security & Reliability
- **API Key Management**: Secure storage and handling of provider credentials
- **Rate Limiting**: Respect provider API limits to avoid service disruption
- **Error Handling**: Comprehensive error handling and recovery mechanisms
- **Logging**: Detailed logging for troubleshooting and audit trails

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager
- Active accounts with supported DNS providers

### Quick Install
```bash
# Clone the repository
git clone https://github.com/Manas-Kushwaha-99/DNS-Manager.git

# Navigate to the project directory
cd DNS-Manager

# Install required dependencies
pip install -r requirements.txt

# Run the application
python DNS-Manager.py
```

### Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv dns-manager-env

# Activate virtual environment
# On Windows:
dns-manager-env\Scripts\activate
# On macOS/Linux:
source dns-manager-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### Provider Setup
1. **Cloudflare**:
   - Obtain API token from Cloudflare dashboard
   - Set required permissions: Zone.Read, Zone.Edit

2. **AWS Route 53**:
   - Configure AWS credentials via AWS CLI or environment variables
   - Ensure appropriate IAM permissions for Route 53

3. **Google Cloud DNS**:
   - Set up service account with DNS admin permissions
   - Download service account key file

### Environment Variables
Create a `.env` file in the project root:
```env
# Cloudflare
CLOUDFLARE_API_TOKEN=your_api_token_here
CLOUDFLARE_EMAIL=your_email@example.com

# AWS Route 53
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Google Cloud DNS
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GCP_PROJECT_ID=your_project_id
```

## Usage

### Basic Operations

#### List DNS Records
```bash
python DNS-Manager.py list --domain example.com --provider cloudflare
```

#### Add DNS Record
```bash
python DNS-Manager.py add --domain example.com --type A --name www --value 192.168.1.1 --ttl 3600
```

#### Update DNS Record
```bash
python DNS-Manager.py update --domain example.com --type A --name www --value 192.168.1.2
```

#### Delete DNS Record
```bash
python DNS-Manager.py delete --domain example.com --type A --name www
```

### Bulk Operations

#### Import from CSV
```bash
python DNS-Manager.py import --file dns-records.csv --domain example.com
```

#### Export to CSV
```bash
python DNS-Manager.py export --domain example.com --output dns-backup.csv
```

### Backup Operations

#### Create Backup
```bash
python DNS-Manager.py backup --domain example.com --output backup-$(date +%Y%m%d).json
```

#### Restore from Backup
```bash
python DNS-Manager.py restore --file backup-20231201.json --domain example.com
```

## Supported Record Types

- **A**: IPv4 address records
- **AAAA**: IPv6 address records
- **CNAME**: Canonical name records
- **MX**: Mail exchange records
- **TXT**: Text records
- **NS**: Name server records
- **PTR**: Pointer records
- **SRV**: Service records
- **SOA**: Start of authority records

## API Reference

### Core Classes

#### DNSManager
Main class for DNS operations
```python
from dns_manager import DNSManager

# Initialize with provider
manager = DNSManager(provider='cloudflare', api_token='your_token')

# List records
records = manager.list_records('example.com')

# Add record
manager.add_record('example.com', 'A', 'www', '192.168.1.1', ttl=3600)
```

#### Record
DNS record representation
```python
class Record:
    def __init__(self, name, type, value, ttl=3600):
        self.name = name
        self.type = type
        self.value = value
        self.ttl = ttl
```

## Configuration File

Create `config.yaml` for advanced configuration:
```yaml
default_provider: cloudflare
default_ttl: 3600
logging:
  level: INFO
  file: dns-manager.log
backup:
  auto_backup: true
  backup_directory: ./backups
  retention_days: 30
validation:
  strict_mode: true
  validate_mx: true
  validate_nameservers: true
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API credentials are correct
   - Check API token permissions
   - Ensure provider account is active

2. **Rate Limiting**
   - Reduce batch sizes
   - Implement delays between requests
   - Check provider rate limits

3. **DNS Propagation**
   - Allow 24-48 hours for global propagation
   - Use DNS checker tools to verify changes
   - Consider lowering TTL values before major changes

### Debug Mode
Run with debug output:
```bash
python DNS-Manager.py --debug list --domain example.com
```

### Log Files
Check log files for detailed error information:
- `dns-manager.log`: General application logs
- `error.log`: Error-specific logs
- `audit.log`: Change history and audit trail

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/your-username/DNS-Manager.git

# Create feature branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run linting
flake8 .
pylint dns_manager/
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write comprehensive docstrings
- Maintain test coverage above 90%

## Testing

### Unit Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=dns_manager

# Run specific test file
python -m pytest tests/test_cloudflare.py
```

### Integration Tests
```bash
# Run integration tests (requires provider credentials)
python -m pytest tests/integration/ --integration
```

## Security

### Best Practices
- Store API credentials securely using environment variables
- Use principle of least privilege for API permissions
- Regularly rotate API keys
- Monitor DNS changes for unauthorized modifications
- Enable two-factor authentication on provider accounts

### Reporting Security Issues
Please report security vulnerabilities to: security@example.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

### Documentation
- [Wiki](https://github.com/Manas-Kushwaha-99/DNS-Manager/wiki)
- [API Documentation](https://dns-manager.readthedocs.io/)
- [Tutorials](https://github.com/Manas-Kushwaha-99/DNS-Manager/tree/main/docs/tutorials)

### Community
- [GitHub Discussions](https://github.com/Manas-Kushwaha-99/DNS-Manager/discussions)
- [Issue Tracker](https://github.com/Manas-Kushwaha-99/DNS-Manager/issues)
- [Discord Server](https://discord.gg/dns-manager)

### Professional Support
For enterprise support and custom integrations, contact: support@example.com

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

## Roadmap

### Upcoming Features
- [ ] Web-based GUI interface
- [ ] DNS analytics and monitoring
- [ ] Automated DNS health checks
- [ ] Integration with CI/CD pipelines
- [ ] Mobile application
- [ ] Advanced DNS security features

### Version 2.0 Goals
- Enhanced performance and scalability
- Additional provider integrations
- Advanced automation capabilities
- Improved user experience

## Acknowledgments

- Thanks to all contributors who have helped improve this project
- Special thanks to the DNS provider APIs that make this tool possible
- Inspired by the need for unified DNS management across multiple providers

---

**Note**: This tool is designed for educational and professional use. Always test DNS changes in a development environment before applying to production systems.

For the latest updates and releases, visit our [GitHub repository](https://github.com/Manas-Kushwaha-99/DNS-Manager).

**Made with ❤️ by [Manas Kushwaha](https://github.com/Manas-Kushwaha-99)**
