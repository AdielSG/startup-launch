// Mock data matching the backend Company schema.
// Loom    → Strong (X: 2,847  LI: 312  — both above threshold)
// Clerk   → Poor   (X:   423  LI:  67  — both below threshold) → red row
// Resend  → Poor   (X:   189  LI:  34  — both below threshold) → red row

export const THRESHOLDS = { xLikes: 500, liLikes: 100 }

export const MOCK_COMPANIES = [
  {
    id: 1,
    name: 'Loom',
    domain: 'loom.com',
    description: 'Async video messaging for teams — record and share in seconds.',
    yc_batch: 'W16',
    founded_year: 2015,
    funding_rounds: [
      { id: 1, amount: 30_000_000, round_type: 'Series B', date: '2021-05-01', source: 'crunchbase' },
    ],
    launch_posts: [
      { id: 1, platform: 'twitter',  likes: 2847, reposts: 634, post_url: 'https://twitter.com/loom/status/1', date: '2021-05-12' },
      { id: 2, platform: 'linkedin', likes: 312,  reposts: null, post_url: null, date: '2021-05-12' },
    ],
    contacts: [{ id: 1, email: 'shaanvp@loom.com', linkedin_url: 'https://linkedin.com/in/shaanvp', x_handle: 'shaanvp' }],
  },
  {
    id: 2,
    name: 'Clerk',
    domain: 'clerk.com',
    description: 'Complete user management platform for React and Next.js apps.',
    yc_batch: 'S21',
    founded_year: 2021,
    funding_rounds: [
      { id: 2, amount: 8_500_000, round_type: 'Seed', date: '2022-03-15', source: 'crunchbase' },
    ],
    launch_posts: [
      { id: 3, platform: 'twitter',  likes: 423, reposts: 89,  post_url: 'https://twitter.com/ClerkDev/status/2', date: '2022-03-20' },
      { id: 4, platform: 'linkedin', likes: 67,  reposts: null, post_url: null, date: '2022-03-20' },
    ],
    contacts: [{ id: 2, email: 'colin@clerk.com', linkedin_url: 'https://linkedin.com/company/clerkdev', x_handle: 'ClerkDev' }],
  },
  {
    id: 3,
    name: 'Resend',
    domain: 'resend.com',
    description: 'Email API for developers. Build and ship transactional email at scale.',
    yc_batch: 'W23',
    founded_year: 2023,
    funding_rounds: [
      { id: 3, amount: 3_000_000, round_type: 'Seed', date: '2023-02-07', source: 'crunchbase' },
    ],
    launch_posts: [
      { id: 5, platform: 'twitter',  likes: 189, reposts: 28,  post_url: 'https://twitter.com/resendlabs/status/3', date: '2023-03-12' },
      { id: 6, platform: 'linkedin', likes: 34,  reposts: null, post_url: null, date: '2023-03-12' },
    ],
    contacts: [{ id: 3, email: 'zeno@resend.com', linkedin_url: 'https://linkedin.com/company/resend', x_handle: 'resendlabs' }],
  },
]

// ── Derived helpers ───────────────────────────────────────────────────────────

export const getPost    = (c, platform) => c.launch_posts.find(p => p.platform === platform) ?? null
export const getXPost   = c => getPost(c, 'twitter')
export const getLiPost  = c => getPost(c, 'linkedin')
export const getXLikes  = c => getXPost(c)?.likes  ?? null
export const getLiLikes = c => getLiPost(c)?.likes ?? null

export const getTotalFunding = c =>
  c.funding_rounds.reduce((s, r) => s + (r.amount ?? 0), 0)

export function isPoorPerformer(company, thresholds = THRESHOLDS) {
  const x  = getXLikes(company)
  const li = getLiLikes(company)
  // Both values must be known AND both must be below their threshold
  return x !== null && li !== null && x < thresholds.xLikes && li < thresholds.liLikes
}

export function formatFunding(amount) {
  if (!amount) return '—'
  if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`
  return `$${(amount / 1e3).toFixed(0)}K`
}

export function generateMockDm(company) {
  const x       = getXLikes(company)
  const li      = getLiLikes(company)
  const funding = formatFunding(getTotalFunding(company))

  return `Hi ${company.name} team,

I came across your launch on X — ${company.description} Really impressive work.

Looking at the numbers (${x?.toLocaleString() ?? '—'} X likes, ${li?.toLocaleString() ?? '—'} LinkedIn engagements), it seems like the launch didn't quite get the traction a ${funding}-funded, YC ${company.yc_batch} product deserves.

I help early-stage founders turn underwhelming launches into proper growth moments — usually through a mix of developer community seeding, narrative sharpening, and targeted distribution across the right channels.

I'd love to share a few specific observations on what I'd try differently for ${company.name}. Would you be open to a 15-minute call this week? No pitch, just some honest feedback.

Best,
[Your Name]`
}
