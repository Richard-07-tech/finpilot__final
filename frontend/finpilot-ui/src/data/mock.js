// ---------------------------------------------------------------------------
// FinPilot / Vantage Finance — UI configuration & text constants.
// Only contains UI chrome (nav labels, user info, suggested prompts,
// institution list, format rules, etc.) — no fake financial data.
// ---------------------------------------------------------------------------

export const user = {
  firstName: 'Maya',
  fullName: 'Maya Hartwell',
  plan: 'Premium Plan',
  initials: 'MH',
  botInitials: 'V',
}

export const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: 'grid', crumb: 'Dashboard' },
  { to: '/chat', label: 'Chat Q&A', icon: 'chat', crumb: 'Chat Q&A' },
  { to: '/summary', label: 'Monthly Summary', icon: 'report', crumb: 'Monthly Summary' },
  { to: '/upload', label: 'Upload Flow', icon: 'upload', crumb: 'Upload Flow' },
  { to: '/transactions', label: 'Transaction List', icon: 'list', crumb: 'Transaction List' },
]

// ---- Chat Q&A (UI text only) -----------------------------------------------
export const chat = {
  suggestedPrompts: [
    'Monthly spending summary',
    'Compare this month to last',
    'Identify recurring subscriptions',
    'Analyze lifestyle budget',
  ],
  inputPlaceholder: 'Ask Vantage...',
}

// ---- Upload Flow (UI text only) --------------------------------------------
export const upload = {
  eyebrow: 'Data Intake',
  heading: 'Statement Import',
  description:
    'Bring your history with you. Drop in bank or card statements and Vantage will parse, categorize, and reconcile them against your existing ledger — usually in under a minute.',
  drop: {
    heading: 'Import your financial data',
    helper: 'Drag and drop your bank statements (.pdf, .csv, .xlsx) here, or click to browse',
    button: 'Select Files',
  },
  institutions: [
    { name: 'Chase', color: '#2F6FBF' },
    { name: 'Bank of America', color: '#C0392B' },
    { name: 'Wells Fargo', color: '#C9A227' },
    { name: 'American Express', color: '#2E86AB' },
    { name: 'Capital One', color: '#7E7668' },
    { name: 'Citibank', color: '#3E5C76' },
  ],
  moreInstitutions: '+14 more',
  formatTitle: 'Format Requirements',
  formatRules: [
    'PDF, CSV, or XLSX exported directly from your bank portal',
    'One account per file, with transaction tables or header rows',
    'Columns: date, description, amount (debits and credits supported)',
    'Text-based PDFs and UTF-8 files up to 25 MB supported',
  ],
  trustLine:
    '\u201COver 2.1 million statements parsed with 99.4% categorization accuracy. Your files are encrypted in transit and at rest, and never used to train models.\u201D',
  footer: {
    status: 'Operational',
    links: ['Data Privacy', 'Integration Guide', 'Contact Support'],
  },
}

// ---- Transactions (category list for picker) --------------------------------
export const categories = [
  'Groceries', 'Dining', 'Transport', 'Shopping', 'Utilities',
  'Health & Wellness', 'Entertainment', 'Income', 'Transfer', 'Uncategorized',
  'Food & Dining', 'Transportation', 'Subscriptions', 'Healthcare', 'Travel',
]
