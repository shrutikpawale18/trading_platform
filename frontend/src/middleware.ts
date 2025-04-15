import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  const { pathname } = request.nextUrl;

  // If the user is not authenticated and trying to access protected routes
  if (!token && (pathname.startsWith('/dashboard') || pathname.startsWith('/trading') || pathname.startsWith('/backups'))) {
    return NextResponse.redirect(new URL('/auth/login', request.url));
  }

  // If the user is authenticated and trying to access auth pages
  if (token && (pathname.startsWith('/auth/login') || pathname.startsWith('/auth/register'))) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/trading/:path*', '/backups/:path*', '/auth/:path*'],
}; 