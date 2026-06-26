# Forms — Source References

These are the canonical file paths for the GenericForm system.
Read these when you need implementation details beyond what the SPEC covers.

## Core Components
- `src/components/genericForm/GenericForm.tsx` — main component, all 4 modes
- `src/components/genericForm/GenericInput.tsx` — field wrapper + `FormField`, `FormSection` types
- `src/components/genericForm/inputs/registry.ts` — input registry (how to register custom inputs)
- `src/components/genericForm/inputs/types.ts` — `FormField`, `FieldType` interfaces

## Shared Infrastructure
- `src/shared/utils/payload-builder.ts` — `buildApiPayload`, UUID strategy, `.env` flag
- `src/shared/errors/error-handler.ts` — extensible parser chain (`addErrorParser`)
- `src/shared/errors/toast-adapter.ts` — swappable toast (`notify.error`, `notify.success`)
- `src/shared/errors/types.ts` — `ApiError`, `ParsedError` types
- `src/shared/hooks/useApiCreate.ts` — where `buildApiPayload` is called
- `src/shared/hooks/useApiUpdate.ts` — where `buildApiPayload` is called

## Config
- `.env.local` → `NEXT_PUBLIC_IS_TEST_UUID` — controls UUID generation strategy (library vs manual fallback)
