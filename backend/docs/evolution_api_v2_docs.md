# Documentação Resumida - Evolution API v2 (GhostHub)

Esta é uma compilação das principais configurações, endpoints e comportamentos da **Evolution API v2** (também conhecida em alguns forks como GhostHub) que estamos utilizando no projeto. 

## 1. Webhooks

A versão 2 da Evolution API exige configurações específicas de Webhooks para receber mensagens e status.

### Eventos Disponíveis
- `MESSAGES_UPSERT` (ou `MESSAGES.UPSERT` no corpo do payload dependendo da versão): Recebe mensagens de texto, áudio, imagem, vídeo, etc.
- `CONNECTION_UPDATE`: Atualizações de status da conexão (QR Code, Conectado, Desconectado).
- `SEND_MESSAGE`: Confirmações de envio de mensagem.

### Endpoint para Configurar Webhook
**POST** `/webhook/set/{instance_name}`

**Payload v2**:
```json
{
  "webhook": {
    "enabled": true,
    "url": "https://seu-backend.com/api/v1/webhook/evolution",
    "byEvents": false,
    "base64": false,
    "events": ["MESSAGES_UPSERT"]
  }
}
```

*Nota: Se o webhook não estiver configurado corretamente, o backend não receberá as mensagens do WhatsApp (ficarão paradas na API).*

## 2. Autenticação e Headers

Todas as requisições para a Evolution API precisam dos seguintes Headers:
```json
{
  "apikey": "sua-api-key",
  "Content-Type": "application/json"
}
```
*Na nossa implementação, a API Key é passada como `EVOLUTION_API_KEY` (e em alguns endpoints críticos como criar instância, usa-se `EVOLUTION_GLOBAL_KEY`).*

## 3. Endpoints Principais (Instância)

### Criar Instância
**POST** `/instance/create`
**Payload**:
```json
{
  "instanceName": "nome_da_instancia",
  "token": "token_exclusivo_da_instancia",
  "qrcode": true,
  "integration": "WHATSAPP-BAILEYS"
}
```

### Buscar Status da Conexão
**GET** `/instance/connectionState/{instance_name}`
**Resposta Esperada**:
```json
{
  "instance": {
    "instanceName": "nome",
    "state": "open" // open, connecting, close
  }
}
```

### Buscar QR Code (Conectar)
**GET** `/instance/connect/{instance_name}`
Retorna o QR Code em Base64 na propriedade `base64` ou `qrcode.base64`.

### Desconectar (Logout)
**DELETE** `/instance/logout/{instance_name}`

## 4. Endpoints Principais (Mensagens)

### Enviar Texto
**POST** `/message/sendText/{instance_name}`
```json
{
  "number": "5511999999999",
  "text": "Olá, tudo bem?",
  "delay": 1200
}
```

### Enviar Áudio (Nota de Voz)
Para que o áudio pareça gravado na hora, o endpoint recomendado é `/message/sendWhatsAppAudio` ou `/message/sendMedia` com o tipo específico.
**POST** `/message/sendWhatsAppAudio/{instance_name}`
```json
{
  "number": "5511999999999",
  "audio": "data:audio/ogg;base64,...",
  "delay": 1500
}
```

### Enviar Arquivo / Documento
**POST** `/message/sendMedia/{instance_name}`
```json
{
  "number": "5511999999999",
  "media": "data:text/calendar;base64,...",
  "mediatype": "document",
  "fileName": "arquivo.pdf",
  "caption": "Segue o arquivo"
}
```

## 5. Solução de Problemas Comuns

- **Mensagens não chegam no Backend**: Verifique via `GET /webhook/find/{instance_name}` se o URL do webhook está apontando corretamente para o backend e se o evento `MESSAGES_UPSERT` está habilitado.
- **Formato do Evento no Webhook**: No Roteador (Message Processor) do backend, atente-se ao formato do payload recebido. Na v2, o nome do evento costuma vir no campo `event` como `MESSAGES.UPSERT` (em maiúsculo).
- **Erro 403 Forbidden ao criar instância**: Significa que a instância com aquele nome já existe. Se isso ocorrer, basta utilizar os endpoints normais de conexão.
