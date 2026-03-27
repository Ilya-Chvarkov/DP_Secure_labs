from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime


def generate_self_signed_cert(cert_path, key_path):
    # Генерируем приватный ключ
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Создаем самоподписанный сертификат
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"RU"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Moscow"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Moscow"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SSL Lab"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"127.0.0.1"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"127.0.0.1")]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Сохраняем приватный ключ
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Сохраняем сертификат
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f" Создан: {cert_path} и {key_path}")


if __name__ == "__main__":
    # Создаем сертификат A
    generate_self_signed_cert("certA.pem", "keyA.pem")

    # Создаем сертификат B
    generate_self_signed_cert("certB.pem", "keyB.pem")

    print("\n Все сертификаты созданы!")