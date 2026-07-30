import client from './client'

export const conversationsAPI = {
  list: () => client.get('/conversations'),
  get: (id) => client.get(`/conversations/${id}`),
  meta: (id) => client.get(`/conversations/${id}/meta`),
  create: (data) => client.post('/conversations', data),
  update: (id, data) => client.patch(`/conversations/${id}`, data),
  delete: (id) => client.delete(`/conversations/${id}`),
}
