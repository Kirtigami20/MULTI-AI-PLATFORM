import client from './client'

export const knowledgeAPI = {
  list: () => client.get('/knowledge'),
  get: (id) => client.get(`/knowledge/${id}`),
  create: (data) => client.post('/knowledge', data),
  delete: (id) => client.delete(`/knowledge/${id}`),
  chunks: (id, params) => client.get(`/knowledge/${id}/chunks`, { params }),
}
