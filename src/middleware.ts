import { NextResponse, type NextRequest } from "next/server";

/**
 * Public site is in under-construction mode.
 * All app/marketing routes redirect to the landing page.
 * Static assets and Next internals are excluded via the matcher.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/") {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = "/";
  url.search = "";
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon / icons
     * - under-construction media assets
     * - public static files with extensions
     */
    "/((?!_next/static|_next/image|favicon\\.ico|icon\\.svg|under-construction/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|mp4|ico|txt|xml)$).*)",
  ],
};
