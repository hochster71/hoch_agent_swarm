# TLS Scaffolding and Reverse Proxy Templates
import ssl

def get_production_ssl_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """
    Creates a secure SSL context enforcing TLS 1.3 for production transport security.
    """
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
    return context

NGINX_PROXY_TEMPLATE = """
server {
    listen 443 ssl http2;
    server_name control-plane.internal;

    ssl_certificate /etc/ssl/certs/control-plane.crt;
    ssl_certificate_key /etc/ssl/private/control-plane.key;
    ssl_protocols TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
