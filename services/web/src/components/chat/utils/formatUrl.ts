/**
 * Format URL for compact display with intelligent truncation
 * - Short URLs: Show full (e.g., "example.com/page")
 * - Long URLs: Truncate middle (e.g., "example.com/.../page")
 * - Max length: ~40 characters
 */
export function formatCompactUrl(url: string, maxLength = 40): string {
  try {
    const urlObj = new URL(url);
    const domain = urlObj.hostname.replace('www.', '');
    const path = urlObj.pathname + urlObj.search;
    const cleanPath = path.endsWith('/') ? path.slice(0, -1) : path;
    const fullUrl = domain + cleanPath;

    if (fullUrl.length <= maxLength) return fullUrl;

    const pathParts = cleanPath.split('/').filter(Boolean);
    if (pathParts.length > 2) {
      return `${domain}/${pathParts[0]}/.../${pathParts[pathParts.length - 1]}`;
    }

    if (cleanPath.length > 25) {
      return `${domain}${cleanPath.substring(0, 22)}...`;
    }

    return fullUrl;
  } catch {
    return url.substring(0, maxLength) + (url.length > maxLength ? '...' : '');
  }
}
