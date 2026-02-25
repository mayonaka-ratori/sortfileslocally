import { getRequestConfig } from 'next-intl/server';
import { cookies } from 'next/headers';

export default getRequestConfig(async () => {
    // Try to get locale from cookie, fallback to 'en'
    const cookieStore = await cookies();
    const locale = cookieStore.get('NEXT_LOCALE')?.value || 'en';

    return {
        locale,
        messages: (await import(`../messages/${locale}.json`)).default
    };
});
