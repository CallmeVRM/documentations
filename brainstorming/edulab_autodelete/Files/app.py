from flask import Flask, render_template, request
import subprocess
import random
import string
import ipaddress
from flask_sock import Sock
import os
import pty
import threading
from datetime import datetime, timedelta
from models import db, Lab, Container
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from sqlalchemy import func
from models import Container


app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'
sock = Sock(app)

# Définir les paramètres de la plage de sous-réseaux
START_SUBNET = ipaddress.IPv4Network('10.0.100.0/28')
END_SUBNET = ipaddress.IPv4Network('10.0.200.0/28')

# Configuration de la base de données PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://adminlocal:password@localhost/file_transfer'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser la base de données avec l'application Flask
db.init_app(app)

# Durée du lab en minutes
LAB_DURATION_MINUTES = 2

# Dictionnaire pour stocker les noms de conteneurs créés, avec leur hostname comme clé
created_containers = {}

# Configuration du planificateur pour supprimer les laboratoires expirés
scheduler = BackgroundScheduler()

# Tester la requête
with app.app_context():
    container = Container.query.filter_by(nom="admin-pc_6370").first()
    print(container)  # Cela devrait afficher les détails du conteneur si trouvé

def is_subnet_available(subnet, existing_subnets):
    """Vérifie si un sous-réseau est disponible parmi les sous-réseaux existants."""
    for existing_subnet in existing_subnets:
        if subnet.overlaps(existing_subnet):
            return False
    return True

def get_available_subnet():
    """Parcourt la plage de sous-réseaux pour en trouver un disponible."""
    try:
        # Obtenir la liste des sous-réseaux existants
        result = subprocess.run(
            ['docker', 'network', 'ls', '-q'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        network_ids = result.stdout.strip().splitlines()
        existing_subnets = set()
        for network_id in network_ids:
            result = subprocess.run(
                ['docker', 'network', 'inspect', network_id, '--format', '{{range .IPAM.Config}}{{.Subnet}}{{end}}'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            subnet_str = result.stdout.strip()
            if subnet_str:
                existing_subnets.add(ipaddress.IPv4Network(subnet_str))

        # Parcourir la plage de sous-réseaux pour trouver un sous-réseau disponible
        current_subnet = START_SUBNET
        while current_subnet.network_address <= END_SUBNET.network_address:
            if is_subnet_available(current_subnet, existing_subnets):
                return current_subnet
            next_network_address = int(current_subnet.network_address) + current_subnet.num_addresses
            current_subnet = ipaddress.IPv4Network(f"{ipaddress.IPv4Address(next_network_address)}/{current_subnet.prefixlen}", strict=False)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la récupération des réseaux existants : {e.stderr.strip()}")
    return None

def delete_expired_labs():
    """Supprime les laboratoires expirés commençant par 'file_transfer_'."""
    with app.app_context():
        now = datetime.utcnow()

        # Récupérer les laboratoires expirés
        expired_labs = Lab.query.filter(
            Lab.nom.startswith("file_transfer_"),
            Lab.heure_creation <= now - timedelta(minutes=LAB_DURATION_MINUTES)
        ).all()

        for lab in expired_labs:
            containers = lab.containers
            for container in containers:
                try:
                    subprocess.run(['docker', 'rm', '-f', container.nom], check=True)
                    db.session.delete(container)
                    created_containers.pop(container.hostname, None)  # Supprimer du dictionnaire
                except subprocess.CalledProcessError as e:
                    print(f"Erreur lors de la suppression du conteneur {container.nom} : {e}")

            try:
                subprocess.run(['docker', 'network', 'rm', lab.network_name], check=True)
                db.session.delete(lab)
            except subprocess.CalledProcessError as e:
                print(f"Erreur lors de la suppression du réseau {lab.network_name} : {e}")

        db.session.commit()

scheduler.add_job(func=delete_expired_labs, trigger="interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-lab', methods=['POST'])
def start_lab():
    # Générer automatiquement un nom unique pour le lab
    random_suffix = ''.join(random.choices(string.digits, k=4))
    lab_name = f"file_transfer_{random_suffix}"
    network_name = lab_name

    # Obtenir un sous-réseau disponible
    subnet = get_available_subnet()
    if not subnet:
        message = "Aucun sous-réseau disponible dans la plage spécifiée."
        return render_template('result.html', message=message)

    # Créer le réseau Docker avec le sous-réseau disponible
    try:
        result = subprocess.run(
            ['docker', 'network', 'create', f'--subnet={subnet}', network_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        network_id = result.stdout.strip()
        message = f"Réseau créé avec succès : {network_id}<br>Nom du réseau : {network_name}<br>Sous-réseau : {subnet}"
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        message = f"Erreur lors de la création du réseau : {error_message}"
        return render_template('result.html', message=message)

    containers = [
        {'hostname': 'admin-pc', 'ip_suffix': 2},
        {'hostname': 'web-server', 'ip_suffix': 3},
        {'hostname': 'backup', 'ip_suffix': 4}
    ]


    container_info = {}
    for container in containers:
        container_name = f"{container['hostname']}_{random_suffix}"  # Nom complet avec suffixe aléatoire
        container_ip = str(ipaddress.IPv4Address(int(subnet.network_address) + container['ip_suffix']))
        cmd = [
            'docker', 'run', '-d',
            '--hostname', container['hostname'],  # Le hostname reste simple (ex: admin-pc)
            '--name', container_name,  # Nom complet du conteneur
            '--network', network_name,
            '--ip', container_ip,
            'file_lab'
        ]
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            container_id = result.stdout.strip()
            message += f"<br>Conteneur créé : {container_name} (ID: {container_id})"
            # Stocker les informations dans container_info avec le nom complet
            container_info[container_name] = {'container_name': container_name, 'ip': container_ip}
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            message += f"<br>Erreur lors de la création du conteneur {container_name} : {error_message}"

    try:
        with app.app_context():
            new_lab = Lab(
                nom=lab_name,
                heure_creation=datetime.utcnow(),
                network_name=network_name,
                subnet=str(subnet),
                duree=LAB_DURATION_MINUTES
            )
            db.session.add(new_lab)
            db.session.commit()
            for container_name, info in container_info.items():
                # Enregistrer chaque conteneur avec le nom complet dans la base de données
                new_container = Container(
                    lab_id=new_lab.id,
                    nom=info['container_name'],  # Nom complet du conteneur
                    hostname=container_name.split('_')[0],  # Nom de base pour le hostname
                    ip_address=info['ip'],
                    heure_creation=datetime.utcnow()
                )
                db.session.add(new_container)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        message = f"Erreur lors de l'enregistrement dans la base de données : {e}"
        return render_template('result.html', message=message)

    expiration_time = datetime.utcnow() + timedelta(minutes=LAB_DURATION_MINUTES)

    return render_template(
        'result.html',
        message=message,
        container_info=container_info,  # Utiliser le nom complet dans container_info
        expiration_time=expiration_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    )

@app.route('/terminal/<hostname>')
def terminal(hostname):
    # Utiliser le nom complet pour rechercher dans la base de données
    container = Container.query.filter_by(nom=hostname).first()
    if not container:
        return f"Conteneur {hostname} non trouvé.", 404

    return render_template('terminal.html', hostname=container.nom)  # Utiliser le nom complet

@sock.route('/ws/<hostname>')
def ws(sock, hostname):
    container = Container.query.filter_by(nom=hostname).first()  # Utiliser le nom complet
    if not container:
        sock.close()
        return

    container_name = container.nom
    cmd = ['docker', 'exec', '-it', container_name, 'bash']
    master_fd, slave_fd = pty.openpty()

    try:
        p = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            universal_newlines=True
        )

        # Fonction pour lire depuis le processus Docker et envoyer au client
        def read_from_docker():
            try:
                while True:
                    data = os.read(master_fd, 1024)
                    if data:
                        sock.send(data.decode())
                    else:
                        break
            except Exception as e:
                print(f"Erreur dans read_from_docker : {e}")
            finally:
                sock.close()

        # Fonction pour lire depuis le client et écrire au processus Docker
        def write_to_docker():
            try:
                while True:
                    data = sock.receive()
                    if data:
                        os.write(master_fd, data.encode())
                    else:
                        break
            except Exception as e:
                print(f"Erreur dans write_to_docker : {e}")
            finally:
                p.terminate()
                os.close(master_fd)
                os.close(slave_fd)

        read_thread = threading.Thread(target=read_from_docker)
        write_thread = threading.Thread(target=write_to_docker)

        read_thread.start()
        write_thread.start()

        read_thread.join()
        write_thread.join()
    except Exception as e:
        print(f"Erreur dans la connexion WebSocket : {e}")
        sock.close()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
