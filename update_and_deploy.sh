#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuración
ACR_NAME="acrmaxamlab"
IMAGE_NAME="risk-analyzer"
ACR_LOGIN_SERVER="$ACR_NAME.azurecr.io"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NEW_TAG="v_$TIMESTAMP"

echo -e "${BLUE}🚀 Iniciando proceso de actualización y despliegue${NC}"
echo -e "${BLUE}📅 Version: $NEW_TAG${NC}"

# Función para manejar errores
handle_error() {
    echo -e "${RED}❌ Error: $1${NC}"
    exit 1
}

# 1. Login en Azure y ACR
echo -e "\n${BLUE}1. Iniciando sesión en Azure Container Registry...${NC}"
az acr login --name $ACR_NAME || handle_error "No se pudo iniciar sesión en ACR"

# 2. Construir nueva imagen
echo -e "\n${BLUE}2. Construyendo nueva imagen Docker...${NC}"
docker build -t $IMAGE_NAME:$NEW_TAG . || handle_error "Error al construir la imagen"

# 3. Etiquetar imagen para ACR
echo -e "\n${BLUE}3. Etiquetando imagen para ACR...${NC}"
docker tag $IMAGE_NAME:$NEW_TAG $ACR_LOGIN_SERVER/$IMAGE_NAME:$NEW_TAG || handle_error "Error al etiquetar la imagen"
docker tag $IMAGE_NAME:$NEW_TAG $ACR_LOGIN_SERVER/$IMAGE_NAME:latest || handle_error "Error al etiquetar la imagen como latest"

# 4. Subir imagen a ACR
echo -e "\n${BLUE}4. Subiendo imagen a Azure Container Registry...${NC}"
docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:$NEW_TAG || handle_error "Error al subir la imagen con tag específico"
docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:latest || handle_error "Error al subir la imagen latest"

# 5. Configurar Web App para usar :latest y habilitar CD (si existe)
echo -e "\n${BLUE}5. Configurando Web App para despliegue continuo con :latest...${NC}"
WEB_APP_NAME="risk-analyzer-app"
RESOURCE_GROUP="RG-MAXAM-LAB"
DESIRED_IMAGE="$ACR_LOGIN_SERVER/$IMAGE_NAME:latest"

if az account show >/dev/null 2>&1 && az webapp show --name "$WEB_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    CURRENT_IMAGE=$(az webapp config container show \
        --name "$WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query dockerCustomImageName -o tsv 2>/dev/null || echo "")

    if [[ "$CURRENT_IMAGE" != "$DESIRED_IMAGE" || -z "$CURRENT_IMAGE" ]]; then
        echo -e "Actualizando imagen de la Web App a: $DESIRED_IMAGE"
        REGISTRY_CREDS=""
        if [[ -n "${ACR_USERNAME:-}" && -n "${ACR_PASSWORD:-}" ]]; then
            REGISTRY_CREDS="--docker-registry-server-user $ACR_USERNAME --docker-registry-server-password $ACR_PASSWORD"
        fi
        az webapp config container set \
            --name "$WEB_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --docker-custom-image-name "$DESIRED_IMAGE" \
            --docker-registry-server-url "https://$ACR_LOGIN_SERVER" \
            $REGISTRY_CREDS || handle_error "Error al configurar la imagen en la Web App"
    else
        echo -e "La Web App ya apunta a: $DESIRED_IMAGE"
    fi

    echo -e "Habilitando despliegue continuo (CD) desde ACR..."
    az webapp deployment container config --enable-cd true \
        --name "$WEB_APP_NAME" --resource-group "$RESOURCE_GROUP" || handle_error "Error al habilitar CD"

    # Reinicio sólo si cambiamos algo
    if [[ "$CURRENT_IMAGE" != "$DESIRED_IMAGE" || -z "$CURRENT_IMAGE" ]]; then
        echo "Reiniciando Web App para aplicar cambios de configuración..."
        az webapp restart --name "$WEB_APP_NAME" --resource-group "$RESOURCE_GROUP" || handle_error "Error al reiniciar la Web App"
    else
        echo -e "CD activado. Las próximas actualizaciones de :latest se aplicarán automáticamente."
    fi
elif ! az account show >/dev/null 2>&1; then
    echo -e "${BLUE}Saltando configuración de Web App: no hay sesión de Azure. Los pushes a :latest seguirán funcionando en ACR.${NC}"
else
    echo -e "${BLUE}Web App no encontrada. Si necesitas crearla, usa el portal de Azure o 'az webapp create'.${NC}"
fi

# 6. Limpieza de imágenes locales antiguas
echo -e "\n${BLUE}6. Limpiando imágenes locales antiguas...${NC}"
docker image prune -f

echo -e "\n${GREEN}✅ Proceso completado exitosamente${NC}"
echo -e "${GREEN}📦 Nueva imagen: $ACR_LOGIN_SERVER/$IMAGE_NAME:$NEW_TAG${NC}"
echo -e "${GREEN}🔄 También actualizada como: $ACR_LOGIN_SERVER/$IMAGE_NAME:latest${NC}"
