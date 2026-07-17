import { ImageResponse } from 'next/og'

export const size = { width: 32, height: 32 }
export const contentType = 'image/png'

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 32,
          height: 32,
          background: '#09090b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 4,
          border: '1px solid #16a34a',
        }}
      >
        <div
          style={{
            width: 14,
            height: 14,
            border: '2px solid #4ade80',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div style={{ width: 4, height: 4, background: '#4ade80', borderRadius: '50%' }} />
        </div>
      </div>
    ),
    { ...size }
  )
}
