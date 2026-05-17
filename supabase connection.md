1. Install packages
Run this command to install the required dependencies.
Details:
npm install @supabase/supabase-js @supabase/ssr
Code:
File: Code
```
npm install @supabase/supabase-js @supabase/ssr
```

2. Add Supabase UI components
Run this command to install the Supabase shadcn components.
Details:
npx shadcn@latest add @supabase/supabase-client-nextjs
Code:
File: Code
```
npx shadcn@latest add @supabase/supabase-client-nextjs
```

3. Set env variables
Add the following values to your env file.
Code:
File: .env.local
```
NEXT_PUBLIC_SUPABASE_URL=https://pyuiezywvwgfnuyaakzo.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_NbWG7uDbVdgGfdM_oxQPGA_hBT9vd8_
```

4. Check out more UI components
Add auth, realtime and storage functionality to your project
Details:
Explore supabase.com/ui

5. Install Agent Skills (Optional)
Agent Skills give AI coding tools ready-made instructions, scripts, and resources for working with Supabase more accurately and efficiently.
Details:
npx skills add supabase/agent-skills
Code:
File: Code
```
npx skills add supabase/agent-skills
```