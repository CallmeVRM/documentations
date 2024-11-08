from flask import Flask, render_template, request
import subprocess
import random
import string
import ipaddress

app = Flask(__name__)

# Paramètres pour la plage de sous-réseaux
START_SUBNET = ipaddress.IPv4Network('10.0.100.0/28')
END_SUBNET = ipaddress.IPv4Network('10.0.200.0/28')

# Noms des images Docker (modifiables)
IMAGE_ADMIN_PC = 'file_lab'
IMAGE_WEB_SERVER = 'file_lab'
IMAGE_BACKUP = 'file_lab'  # Modifiez si nécessaire

def is_subnet_available(subnet, existing_subnets):
    for existing_subnet in existing_subnets:
        if subnet.overlaps(existing_subnet):
            return False
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-lab', methods=['POST'])
def start_lab():
    # Générer un nom de réseau aléatoire
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    network_name = f"filetransfer_{random_suffix}"

    # Obtenir la liste des sous-réseaux existants
    try:
        # Obtenir les IDs des réseaux existants
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
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        message = f"Erreur lors de la récupération des réseaux existants : {error_message}"
        return render_template('result.html', message=message)

    # Générer les sous-réseaux et en trouver un qui est disponible
    subnet = None
    current_subnet = START_SUBNET
    while current_subnet.network_address <= END_SUBNET.network_address:
        if is_subnet_available(current_subnet, existing_subnets):
            subnet = current_subnet
            break
        # Passer au sous-réseau suivant
        next_network_address = int(current_subnet.network_address) + current_subnet.num_addresses
        current_subnet = ipaddress.IPv4Network(f"{ipaddress.IPv4Address(next_network_address)}/{current_subnet.prefixlen}", strict=False)
    if not subnet:
        message = "Aucun sous-réseau disponible dans la plage spécifiée."
        return render_template('result.html', message=message)

    # Commande Docker pour créer le réseau
    command = [
        'docker', 'network', 'create',
        f'--subnet={subnet}',
        network_name
    ]
    try:
        # Exécuter la commande Docker pour créer le réseau
        result = subprocess.run(
            command,
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

    # Créer les conteneurs
    # Liste des conteneurs à créer
    containers = [
        {
            'hostname': 'admin-pc',
            'image': IMAGE_ADMIN_PC,
            'ip_suffix': 2
        },
        {
            'hostname': 'web-server',
            'image': IMAGE_WEB_SERVER,
            'ip_suffix': 3
        },
        {
            'hostname': 'backup',
            'image': IMAGE_BACKUP,
            'ip_suffix': 4
        }
    ]

    container_names = []
    for container in containers:
        # Générer un nom de conteneur aléatoire
        container_name = f"{container['hostname']}_{random_suffix}"
        # Calculer l'adresse IP du conteneur
        container_ip = str(ipaddress.IPv4Address(int(subnet.network_address) + container['ip_suffix']))
        # Commande pour créer le conteneur
        cmd = [
            'docker', 'run', '-d',
            '--hostname', container['hostname'],
            '--name', container_name,
            '--network', network_name,
            '--ip', container_ip,
            container['image']
        ]
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            container_id = result.stdout.strip()
            message += f"<br>Conteneur créé : {container_name} (ID: {container_id})<br>Hostname : {container['hostname']}<br>IP : {container_ip}"
            container_names.append(container_name)
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            message += f"<br>Erreur lors de la création du conteneur {container_name} : {error_message}"

    return render_template('result.html', message=message)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
