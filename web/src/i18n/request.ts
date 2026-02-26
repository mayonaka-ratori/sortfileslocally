import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async () => {
    // Standard config for static export. 
    // Actual locale is handled by I18nProvider on client side.
    const locale = 'en';

    return {
        locale,
        messages: (await import(`../../messages/${locale}.json`)).default
    };
});
