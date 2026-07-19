# VPN Access & Remote Work Guide

**Document ID:** IT-POL-002  
**Effective Date:** March 1, 2026  
**Last Reviewed:** July 1, 2026  
**Owner:** Network Operations Team — TechCorp Inc.

---

## Overview

TechCorp Inc. provides VPN access to employees who need secure remote connectivity to corporate resources. All remote work must comply with this guide and the company's Remote Work Agreement.

## How to Request VPN Access

1. Submit an IT ticket at [https://helpdesk.techcorp.com](https://helpdesk.techcorp.com) under the category **"Network & VPN Access."**
2. Your **direct manager** must approve the request within the ticketing system.
3. Once approved, the Network Operations team will provision your VPN profile within **2 business days**.
4. You will receive setup instructions via email upon provisioning.

## Supported VPN Client

- **Palo Alto GlobalProtect** is the only approved VPN client at TechCorp Inc.
- Download links and installation guides are available on the IT Self-Service Portal.
- Supported platforms: **Windows 10/11**, **macOS 12+**, **iOS 16+**, and **Android 13+**.

## Troubleshooting Common VPN Issues

If you are unable to connect, try the following steps in order:

1. **Restart the GlobalProtect client** and attempt to reconnect.
2. **Verify your internet connection** — ensure you can browse external websites.
3. **Clear the GlobalProtect cache:** Go to Settings → Troubleshooting → Clear Cache.
4. **Re-authenticate:** Sign out of GlobalProtect completely and sign back in with your corporate credentials.
5. **Restart your device** and try again.
6. If the issue persists, **submit an IT ticket** with screenshots of any error messages and your device's diagnostic logs (Settings → Troubleshooting → Export Logs).

## Split-Tunneling Policy

- **Split tunneling is enabled by default** for general internet traffic (e.g., streaming, personal browsing).
- All traffic to **internal corporate resources** (intranet, file servers, internal apps) is routed through the VPN tunnel.
- Employees handling **Confidential or Restricted data** must enable **full-tunnel mode** via GlobalProtect settings.

## VPN Usage Monitoring

- VPN connections are **logged and monitored** for security purposes, including connection timestamps, duration, and bandwidth usage.
- Unusual activity (e.g., excessive data transfers, connections from restricted geographies) may trigger a security review.
- TechCorp Inc. reserves the right to terminate VPN sessions that violate company policy.

---

*For VPN support, contact the IT Helpdesk at helpdesk@techcorp.com or ext. 4350.*
