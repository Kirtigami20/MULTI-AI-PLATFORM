import client from './client'

export const agentsAPI = {
  list: () => client.get('/agents'),
  get: (id) => client.get(`/agents/${id}`),
  create: (data) => client.post('/agents', data),
  update: (id, data) => client.put(`/agents/${id}`, data),
  delete: (id) => client.delete(`/agents/${id}`),
}
