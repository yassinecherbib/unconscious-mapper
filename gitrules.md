# Git Execution Rules

When instructed to commit or push changes, you must adhere strictly to these operational constraints.

## 1. Operational Scope
- **ALLOWED:** `git add`, `git commit`, `git push`, `git pull`, `git checkout`, `git stash`.
- **FORBIDDEN:** Any file modification, refactoring, bug fixing, or linting during the git workflow.

## 2. Execution Protocol
- **No Implicit Actions:** Do not attempt to "fix" issues mentioned in the commit message. Even if a bug is identified during the process, your task is solely the version control operation.
- **Strict Command Chain:** Execute the specific git commands requested and nothing else. 
- **Message Integrity:** Use the commit message provided. Do not append additional technical metadata or change the description to match what you "think" was changed.

## 3. Workflow
1. Stage files (`git add`).
2. Commit with the provided message (`git commit -m "..."`).
3. Push to the remote repository (`git push`).

Do not deviate. Do not analyze the codebase. Do not edit files.