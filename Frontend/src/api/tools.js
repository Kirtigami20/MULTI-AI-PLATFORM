import client from './client'

export const toolsAPI = {
  list: () => client.get('/tools'),
  get: (id) => client.get(`/tools/${id}`),
  create: (data) => client.post('/tools', data),
  update: (id, data) => client.put(`/tools/${id}`, data),
  delete: (id) => client.delete(`/tools/${id}`),
}
