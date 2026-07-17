import { ImageResponse } from 'next/og'

export const size = { width: 180, height: 180 }
export const contentType = 'image/png'

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 180,
          height: 180,
          background: '#09090b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 40,
          border: '3px solid #16a34a',
        }}
      >
        <div
          style={{
            width: 90,
            height: 90,
            border: '8px solid #4ade80',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div style={{ width: 28, height: 28, background: '#4ade80', borderRadius: '50%' }} />
        </div>
      </div>
    ),
    { ...size }
  )
}
