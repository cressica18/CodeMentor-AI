import { cn } from '@/utils/cn'

interface SkeletonProps {
  className?: string
  style?: React.CSSProperties
}

export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse bg-gradient-to-r from-[#1c1c26] via-[#2a2a3a] to-[#1c1c26] bg-[length:400%_100%] rounded',
        className
      )}
      style={{ animation: 'skeleton-shimmer 1.6s ease-in-out infinite', ...style }}
    />
  )
}

export function ProfileCardSkeleton() {
  return (
    <div className="card p-5 mb-6">
      <div className="flex items-center gap-4">
        <Skeleton className="w-16 h-16 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-48" />
        </div>
        <div className="space-y-2 text-right">
          <Skeleton className="h-7 w-20 ml-auto" />
          <Skeleton className="h-3 w-16 ml-auto" />
        </div>
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="card p-4">
      <Skeleton className="h-3 w-20 mb-2" />
      <Skeleton className="h-7 w-14" />
    </div>
  )
}

export function ChartSkeleton({ height = 220 }: { height?: number }) {
  return (
    <div className="card p-5">
      <Skeleton className="h-4 w-32 mb-4" />
      <Skeleton className="w-full rounded-lg" style={{ height }} />
    </div>
  )
}

export function ProfileLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <ProfileCardSkeleton />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <StatCardSkeleton key={i} />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSkeleton height={240} />
        <ChartSkeleton height={240} />
      </div>
      <ChartSkeleton height={180} />
    </div>
  )
}
