import ssl
import socket
import hashlib
import requests

HOST = '127.0.0.1'
PORT = 5000


# Функция получает сертификат от сервера (без проверки)
def get_server_cert():
    # Создаем контекст, который НЕ проверяет сертификат
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.create_connection((HOST, PORT)) as sock:
        with context.wrap_socket(sock, server_hostname=HOST) as ssock:
            cert = ssock.getpeercert(binary_form=True)
            return cert


# Считаем отпечаток SHA256
def get_cert_fingerprint(cert_bytes):
    return hashlib.sha256(cert_bytes).hexdigest()


# Загружаем наш правильный сертификат A
def get_local_cert():
    with open("certA.pem", "rb") as f:
        cert_data = ssl.PEM_cert_to_DER_cert(f.read().decode())
        return cert_data


if __name__ == "__main__":
    print(" Получаем сертификат сервера...")
    try:
        server_cert = get_server_cert()
        print(" Сертификат получен")
    except Exception as e:
        print(f" Ошибка при получении сертификата: {e}")
        exit(1)

    print("Загружаем локальный сертификат A...")
    try:
        local_cert = get_local_cert()
        print(" Локальный сертификат загружен")
    except Exception as e:
        print(f" Ошибка при загрузке локального сертификата: {e}")
        print(" Убедись, что файл certA.pem существует в папке проекта")
        exit(1)

    server_fp = get_cert_fingerprint(server_cert)
    local_fp = get_cert_fingerprint(local_cert)

    print("\n Отпечаток сертификата сервера: ")
    print(server_fp)
    print("\n Отпечаток локального сертификата A: ")
    print(local_fp)

    if server_fp != local_fp:
        print("\n ОШИБКА: Сертификаты не совпадают!")
        print(" SSL Pinning сработал — соединение заблокировано.")
    else:
        print("\n Сертификаты совпадают! SSL Pinning пройден.")

        # Только если сертификаты совпадают — делаем запрос
        print("\n📡 Загружаем данные с сервера...")
        try:
            # Отключаем проверку сертификата, так как мы уже проверили его сами
            response = requests.get(
                "https://127.0.0.1:5000/stocks-data.json",
                verify=False  # Отключаем стандартную проверку
            )
            print("\n Полученные данные:")
            print(response.json())
        except Exception as e:
            print(f" Ошибка при запросе данных: {e}")