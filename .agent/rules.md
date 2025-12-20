# Role & Philosophy
User is focused on "Cognitive Recovery Cost". Code must be understandable 3 months later.

# Coding Standards (Non-negotiable)
1. **Service/Adapter Pattern**:
   - **Service**: Universal data fetching (e.g., API clients).
   - **Adapter**: Personalized logic/formatting.
   - *Constraint*: Keep them in separate functions/files.
2. **Interface First**:
   - Expose logic via CLI (Typer) + Makefile.
3. **No Hardcoding**:
   - Use `.env` for secrets/paths.
