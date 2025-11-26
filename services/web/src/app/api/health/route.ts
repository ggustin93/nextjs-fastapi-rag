import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json(
    { status: 'healthy', service: 'rag-frontend' },
    { status: 200 }
  );
}

export const dynamic = 'force-dynamic';
