# Clipador AI

MVP web para enviar um vídeo, transcrever falas em português com Whisper e gerar cortes verticais.

## Publicar no Render
1. Crie um repositório público no GitHub e envie todos os arquivos desta pasta.
2. No Render, escolha **New + > Blueprint** e conecte o repositório.
3. O Render detecta `render.yaml`; confirme a criação do serviço.
4. Aguarde o build e abra a URL gerada. Teste `/health`.

## Limitações importantes
- Esta versão processa arquivos enviados pelo usuário. Não baixa vídeos a partir de links do TikTok, YouTube, Twitch ou Kick.
- Os melhores momentos são estimados por uma heurística sobre a transcrição; não é uma IA editorial avançada.
- As legendas são mostradas como texto junto aos links de corte, mas ainda não são gravadas dentro do vídeo.
- O plano gratuito pode hibernar, limitar memória/CPU e não é adequado para vídeos longos. Arquivos no disco podem ser apagados quando a instância reinicia.
- Use apenas vídeos que você tem autorização para baixar e editar.
