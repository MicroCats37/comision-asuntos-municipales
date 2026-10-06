# Stage 1: Dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy installed dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variables for build
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ARG NEXT_PUBLIC_COOKIE_SECURE
ENV NEXT_PUBLIC_COOKIE_SECURE=${NEXT_PUBLIC_COOKIE_SECURE}
ARG NEXT_PUBLIC_IS_TEST_UUID
ENV NEXT_PUBLIC_IS_TEST_UUID=${NEXT_PUBLIC_IS_TEST_UUID}
ARG NEXT_PUBLIC_DEBUG_GENERIC_FORM_ERRORS
ENV NEXT_PUBLIC_DEBUG_GENERIC_FORM_ERRORS=${NEXT_PUBLIC_DEBUG_GENERIC_FORM_ERRORS}
ARG NEXT_PUBLIC_FRONTEND_URL
ENV NEXT_PUBLIC_FRONTEND_URL=${NEXT_PUBLIC_FRONTEND_URL}
ARG NEXT_PUBLIC_AUTH_STORAGE_PREFIX
ENV NEXT_PUBLIC_AUTH_STORAGE_PREFIX=${NEXT_PUBLIC_AUTH_STORAGE_PREFIX}
ENV NEXT_TELEMETRY_DISABLED=1

# Build the Next.js application
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from builder stage
COPY --from=builder /app/public ./public

# Set correct permissions for Next.js standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Expose the port (default: 70020)
EXPOSE ${PORT:-7000}

# Set environment variables with defaults
ENV PORT=${PORT:-7000}
ENV HOSTNAME=${HOSTNAME:-0.0.0.0}

# Start the Next.js standalone server
USER nextjs
CMD ["node", "server.js"]
