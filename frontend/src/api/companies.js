import client from './client'

/**
 * GET /api/companies
 * Returns all companies with funding_rounds, launch_posts, and contacts.
 */
export const fetchCompanies = (params = {}) =>
  client.get('/companies', { params }).then(r => r.data)

/**
 * GET /api/companies/:id/contact
 * Returns the primary contact for a company.
 */
export const fetchContact = (id) =>
  client.get(`/companies/${id}/contact`).then(r => r.data)

/**
 * POST /api/companies/:id/draft-dm
 * Calls OpenAI API and returns { company_id, company_name, dm_text }.
 */
export const draftDm = (id, tone = 'professional') =>
  client.post(`/companies/${id}/draft-dm`, { tone }).then(r => r.data)

/**
 * POST /api/companies/:id/linkedin
 * Saves the LinkedIn post URL and triggers the Apify scraper.
 * Returns { company_id, linkedin_post_url, linkedin_likes, linkedin_reposts, linkedin_fetched_at }.
 * Note: Apify can take up to 60 seconds — set a long axios timeout.
 */
export const submitLinkedinUrl = (id, linkedin_post_url) =>
  client.post(
    `/companies/${id}/linkedin`,
    { linkedin_post_url },
    { timeout: 90_000 },   // 90 s — Apify actor can take up to 60 s
  ).then(r => r.data)

/**
 * POST /api/scraper/run
 * Runs the full scraping pipeline (YC + Twitter) and blocks until complete.
 * Returns { status, companies, tweets } — can take 2-3 minutes for a full batch.
 */
export const triggerScrape = () =>
  client.post('/scraper/run', {}, { timeout: 300_000 }).then(r => r.data)
