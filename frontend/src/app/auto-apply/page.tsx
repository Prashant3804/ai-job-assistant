'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AutoApplyPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/settings/auto-apply');
  }, [router]);
  return null;
}
