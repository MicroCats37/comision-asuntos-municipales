# File Uploads

Two patterns: direct Server Action (small files) and presigned URL (large files to cloud storage).

## Server Action with `FormData`

For files under ~1MB that land directly in your API.

```typescript
'use server';
import { prisma } from '@/infra/prisma/client';

export async function uploadAvatar(formData: FormData) {
  const file = formData.get('avatar') as File;
  
  if (!file || file.size === 0) {
    throw new Error('No file provided');
  }
  
  // Validate on server (always — client validation is UX only)
  if (file.size > 5 * 1024 * 1024) { // 5MB
    throw new Error('File too large (max 5MB)');
  }
  
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    throw new Error('Invalid file type');
  }
  
  const bytes = await file.arrayBuffer();
  const buffer = Buffer.from(bytes);
  
  // Save to disk or upload to cloud
  const filename = `${crypto.randomUUID()}-${file.name}`;
  await saveFile(filename, buffer);
  
  // Update user record
  await prisma.user.update({
    where: { id: getCurrentUserId() },
    data: { avatarUrl: `/uploads/${filename}` }
  });
}
```

**Client side:**
```typescript
<form action={uploadAvatar}>
  <input type="file" name="avatar" accept="image/jpeg,image/png,image/webp" />
  <button type="submit">Upload</button>
</form>
```

---

## Route Handler for Large Streaming Uploads

For files that are too large for a Server Action, use a streaming Route Handler.

```typescript
// app/api/upload/route.ts
import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const file = formData.get('file') as File;
  
  if (!file) return new Response('No file', { status: 400 });
  if (file.size > 100 * 1024 * 1024) return new Response('File too large', { status: 413 });
  
  // Stream to storage (don't buffer in memory)
  const stream = file.stream();
  await saveStream(file.name, stream);
  
  return Response.json({ url: `/uploads/${file.name}` });
}
```

---

## Presigned URL Pattern (S3 / Cloud Storage)

Generate a signed upload URL server-side, let the client upload directly. Your server never sees the file bytes.

```typescript
// app/api/upload/presign/route.ts
import { S3Client } from '@aws-sdk/client-s3';
import { createPresignedPost } from '@aws-sdk/s3-presigned-post';
import { NextResponse } from 'next/server';

const s3 = new S3Client({ region: process.env.AWS_REGION });

export async function POST(req: Request) {
  const { filename, contentType, size } = await req.json();
  
  if (size > 100 * 1024 * 1024) {
    return NextResponse.json({ error: 'File too large' }, { status: 413 });
  }
  
  const { url, fields } = await createPresignedPost(s3, {
    Bucket: process.env.S3_BUCKET!,
    Key: `${crypto.randomUUID()}-${filename}`,
    Conditions: [
      ['content-length-range', 0, 100 * 1024 * 1024],
      ['eq', '$Content-Type', contentType],
    ],
    Fields: { 'Content-Type': contentType },
  });
  
  return NextResponse.json({ url, fields });
}
```

**Client upload:**
```typescript
async function uploadToS3(file: File) {
  const { url, fields } = await fetch('/api/upload/presign', {
    method: 'POST',
    body: JSON.stringify({ filename: file.name, contentType: file.type, size: file.size })
  }).then(r => r.json());
  
  const formData = new FormData();
  Object.entries(fields).forEach(([k, v]) => formData.append(k, v as string));
  formData.append('file', file);
  
  await fetch(url, { method: 'POST', body: formData });
}
```

---

## File Validation Summary

| Check | Client | Server |
|-------|--------|--------|
| File size | UX feedback | Required (client can be bypassed) |
| MIME type | UX feedback | Required |
| Extension | UX feedback | Optional |
| Content scan | No | Yes (production) |

**Always validate on the server.** Client validation is user experience only.
