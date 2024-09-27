##Installation de WireGuard en IPv4 en mode natif sur debian12 : 

### Partie serveur :

Pour une installation stable vous pouvez passer par les sources officiels de debian en exécutant la commande suivante :

```bash
sudo apt update
sudo apt install wireguard
```


Ensuite vous allez générer une paire de clés nécessaires pour l’authentification et le chiffrement des paquets :

```bash
cd /etc/wireguard (umask 277 && wg genkey | tee privatekey | wg pubkey > publickey)
```

En option vous pouvez ajouter une pre-shared key :

```bash
(umask 277 && wg genpsk > /etc/wireguard/psk)
```
La clé pré-partagée (PresharedKey ou PSK) est une amélioration facultative de la sécurité conformément au protocole WireGuard et doit être une PSK unique par client pour une sécurité renforcée. 
En ajoutant une clé pré-partagée (preshared key) dans le processus, on renforce le mécanisme des clés de chiffrement et d'authentification, réduisant ainsi les potentielles attaques futures par ordinateur quantique.


A partie de la vous avez le choix entre deux options :

#### 1. Configurer le serveur WireGuard graduellement et manuellement via des lignes de commandes :

```bash
#Création d'une interface réseau virtuel sous le nom de wg0
ip link add dev wg0 type wireguard
#Ajout d'une IPv4 pour l'interface wg0
ip addr add 10.0.0.1/32 dev wg0
#Ajout d'une IPv6
ip addr add fd12:3456:789a::1/128 dev wg0
#Déclaration du port d'écoute, et du lien vers la clé privé de l'interface wg0
wg set wg0 listen-port 51820 private-key /etc/wireguard/privatekey
#Déclartion du Peer, avec ca clé publique, un keepalive de 25s, et une IP (10.0.0.2/32) autorisée a communiquer avec le serveur
wg set wg0 peer${CLIENT_PUBKEY} persistent-keepalive 25\
    preshared-key /etc/wireguard/psk\
    allowed-ips 10.0.0.2/32,fd12:3456:789a::2/128
#Activation de l'interface wg0
ip link set wg0 up

# Enregistrer la configuration
(umask 077 && wg showconf wg0 > /etc/wireguard/wg0.conf)

#Pour restorer la configuration
wg setconf wg0 /etc/wireguard/wg0.conf
```

#### 2. Configurer le serveur Wireguard via un fichier de configuration :

```bash
[Interface]
Address = 10.0.0.1/32, fd12:3456:789a::1/128
ListenPort = 51820
PrivateKey = <Server wg0 Private Key>
SaveConfig = true

[Peer]
PublicKey = <Client wg0 public key>
#PresharedKey = <Pre-Shared Key>
AllowedIPs = 10.0.0.2/32,fd12:3456:789a::2/128
PersistentKeepalive = 25
```

Il faut ensuite activer le forwarding en ajoutant la ligne suivante dans le fichier /etc/sysctl.conf :

net.ipv4.ip_forward=1

Rendez la configuration persistante avec la commande :

sudo sysctl -p

Si vous avez iptables d'installé, il faut configurer le bon MASQUERADE :

Dans cet exemple, ens18 est mon interface qui fait office de carte réseau physique, et donc c'est à travers elle que les paquets transitent depuis/vers l'extérieur.

```bash
iptables -A FORWARD -i wg0 -o ens18 -j ACCEPT
iptables -t nat -A POSTROUTING -o ens18 -j MASQUERADE
```

Ensuite et finalement vous activez l’interface wg0 :

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

Commandes utiles :