# Frontend Directory Debug
This file is to help debug Vercel deployment issues.

Expected structure:
```
prism-ai-studio/
├── Frontend/          <- This should exist
│   ├── package.json
│   ├── src/
│   └── dist/ (after build)
├── prism-backend/
└── vercel.json
```

If Vercel can't find Frontend/, it might be:
1. Cloning from wrong branch
2. Wrong root directory setting in Vercel dashboard  
3. Cached configuration issue
```