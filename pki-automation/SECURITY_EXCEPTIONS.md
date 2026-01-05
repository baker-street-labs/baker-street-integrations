# Baker Street Labs PKI - Security Exceptions

## 🚨 Security Exception: Online Root CA

### **Exception Details**
- **Component**: Root CA (Tier 0)
- **Standard Practice**: Keep Root CA offline for maximum security
- **Baker Street Labs Exception**: Root CA will remain online for lab operations
- **Risk Level**: Medium-High
- **Justification**: Cyber range operational requirements

### **Background**

In a production enterprise PKI, the Root CA should be kept offline and only powered on for:
1. Signing new subordinate CA certificates
2. Publishing updated Certificate Revocation Lists (CRLs)
3. Emergency operations

This offline approach provides the highest level of security by:
- Eliminating network-based attack vectors
- Preventing remote compromise
- Limiting physical access requirements
- Creating an air-gapped trust anchor

### **Baker Street Labs Exception**

For the Baker Street Labs cyber range environment, we are making a **deliberate security exception** to keep the Root CA online for the following reasons:

#### **Operational Requirements**
- **Rapid Redeployment**: Cyber range scenarios require frequent environment rebuilds
- **Educational Flexibility**: Students and researchers need to experiment with PKI operations
- **Development Testing**: Continuous testing of PKI configurations and scripts
- **Automation Needs**: Scripts and automation require consistent CA availability

#### **Risk Mitigation Measures**
While accepting the online Root CA risk, we implement the following mitigations:

1. **Network Isolation**
   - Root CA on isolated network segment
   - No internet connectivity
   - Restricted firewall rules
   - VPN-only access for management

2. **Access Controls**
   - Limited administrative access
   - Multi-factor authentication
   - Role-based access control
   - Audit logging for all operations

3. **Monitoring and Alerting**
   - Continuous monitoring of CA operations
   - Alert on unauthorized access attempts
   - Regular security scanning
   - Incident response procedures

4. **Backup and Recovery**
   - Daily automated backups
   - Offsite backup storage
   - Tested recovery procedures
   - Documented rollback plans

### **Accepted Risks**

By keeping the Root CA online, we accept the following risks:

1. **Network-Based Attacks**
   - Potential for remote exploitation
   - Increased attack surface
   - Network-based lateral movement

2. **Operational Exposure**
   - Continuous service availability
   - Increased administrative overhead
   - Higher monitoring requirements

3. **Compromise Impact**
   - Potential for complete PKI compromise
   - Need for full PKI rebuild if compromised
   - Impact on all issued certificates

### **Risk Assessment**

| Risk Category | Risk Level | Mitigation | Acceptable |
|---------------|------------|------------|------------|
| Network Attacks | Medium | Network isolation, monitoring | ✅ Yes |
| Physical Access | Low | Physical security controls | ✅ Yes |
| Administrative Error | Medium | Access controls, training | ✅ Yes |
| Malware Infection | Medium | Antivirus, monitoring | ✅ Yes |
| Insider Threat | Low | Access controls, auditing | ✅ Yes |

### **Operational Procedures**

#### **Daily Operations**
- Monitor CA service status
- Review audit logs
- Check backup completion
- Verify network isolation

#### **Weekly Operations**
- Security scan results review
- Access log analysis
- Backup integrity verification
- Update management

#### **Monthly Operations**
- Security assessment
- Penetration testing
- Disaster recovery testing
- Documentation updates

### **Incident Response**

#### **If Root CA is Compromised**
1. **Immediate Response**
   - Isolate Root CA from network
   - Preserve evidence
   - Notify security team
   - Document incident

2. **Recovery Actions**
   - Rebuild Root CA from backup
   - Revoke all issued certificates
   - Re-issue subordinate CA certificates
   - Update all client trust stores

3. **Post-Incident**
   - Root cause analysis
   - Security improvements
   - Process updates
   - Training reinforcement

### **Documentation Requirements**

#### **Security Documentation**
- [ ] Risk assessment documentation
- [ ] Mitigation controls documentation
- [ ] Monitoring procedures
- [ ] Incident response procedures

#### **Operational Documentation**
- [ ] Daily operational procedures
- [ ] Weekly security procedures
- [ ] Monthly assessment procedures
- [ ] Emergency response procedures

### **Approval and Review**

#### **Initial Approval**
- **Date**: 2025-09-29
- **Approved By**: Baker Street Labs Security Team
- **Review Date**: 2026-09-29 (Annual Review)
- **Risk Owner**: PKI Administrator

#### **Review Schedule**
- **Quarterly**: Risk assessment review
- **Annually**: Full security exception review
- **As Needed**: Incident-based review

### **Compliance Notes**

#### **Standards Alignment**
- **NIST SP 800-57**: Acknowledges lab environments may have different requirements
- **ISO 27001**: Risk-based approach to security controls
- **PCI DSS**: Lab environment exemption for educational purposes

#### **Documentation Requirements**
- This exception must be documented in security policies
- Risk assessment must be reviewed annually
- Incident response procedures must be tested
- All stakeholders must be aware of the exception

### **Alternative Considerations**

#### **Future Improvements**
- Consider HSM (Hardware Security Module) for key protection
- Implement additional network segmentation
- Deploy advanced threat detection
- Consider hybrid online/offline approach

#### **Production Migration**
- When moving to production, implement offline Root CA
- Follow industry best practices
- Implement full security controls
- Conduct security assessment

### **Conclusion**

The decision to keep the Root CA online for the Baker Street Labs cyber range is a **deliberate security trade-off** that prioritizes operational flexibility and educational value over maximum security. This exception is:

- **Justified** by the lab environment requirements
- **Mitigated** by appropriate security controls
- **Monitored** through continuous assessment
- **Documented** for compliance and review
- **Reversible** when moving to production

This approach allows the cyber range to fulfill its educational mission while maintaining an acceptable level of security risk for the lab environment.

---

**Document Control**
- **Version**: 1.0
- **Created**: 2025-09-29
- **Last Updated**: 2025-09-29
- **Next Review**: 2026-09-29
- **Owner**: Baker Street Labs Security Team
