const COUNTER_ID = 104746311;

// флаг включения метрики
const enabled =
    typeof window !== 'undefined' &&
    process.env.NODE_ENV === 'production';

/**
 * Хук для работы с Яндекс.Метрикой
 */
export const useYandexMetrika = () => {
    const hit = (url, options) => {
        if (enabled && typeof window.ym === 'function') {
            window.ym(COUNTER_ID, 'hit', url, options);
        } else {
            console.log('[YandexMetrika](hit)', url);
        }
    };

    const reachGoal = (target, params, callback) => {
        if (enabled && typeof window.ym === 'function') {
            window.ym(COUNTER_ID, 'reachGoal', target, params, callback);
        } else {
            console.log('[YandexMetrika](reachGoal)', target, params);
        }
    };

    return { hit, reachGoal };
};

/**
 * Вызов reachGoal без хука (для обработчиков событий)
 */
export const ymReachGoal = (target, params, callback) => {
    if (enabled && typeof window !== 'undefined' && typeof window.ym === 'function') {
        window.ym(COUNTER_ID, 'reachGoal', target, params, callback);
    } else {
        console.log('[YandexMetrika](reachGoal)', target, params);
    }
};
