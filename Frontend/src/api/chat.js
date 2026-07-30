import client from './client'

export const chatAPI = {
  send: (agentId, data) => {
    const payload = { message: data.message }
    if (data.conversation_id) {
      payload.conversation_id = data.conversation_id
    }
    return client.post(`/agents/${agentId}/chat`, payload)
  },
  history: (agentId, limit = 50) =>
    client.get(`/agents/${agentId}/chat`, { params: { limit } }),
  clear: (agentId) => client.delete(`/agents/${agentId}/chat`),
}
