import { useEffect } from 'react';

const COUNTER_ID = 104746311;

export const YandexHit = () => {
    useEffect(() => {
        if (typeof window === 'undefined') return;
        if (typeof window.ym !== 'function') return;

        const sendHit = () => {
            const { pathname, search } = window.location;
            const url = pathname + search;

            window.ym(COUNTER_ID, 'hit', url);
            console.log('YandexHit:', url);
        };

        sendHit();

        // back / forward
        window.addEventListener('popstate', sendHit);

        return () => {
            window.removeEventListener('popstate', sendHit);
        };
    }, []);

    return null;
};
