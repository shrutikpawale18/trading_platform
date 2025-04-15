# Trading Platform Frontend

A modern React-based frontend for the trading platform, built with Next.js, TypeScript, and Tailwind CSS.

## Features

- User authentication (login/register)
- Account dashboard with trading statistics
- Trading interface for placing orders
- Algorithm visualization with moving average crossover
- Real-time updates using React Query
- Responsive design with Tailwind CSS

## Prerequisites

- Node.js 14.x or later
- npm or yarn
- Backend API running (see backend README)

## Setup

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Create a `.env.local` file in the root directory with the following variables:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Start the development server:
```bash
npm run dev
# or
yarn dev
```

The application will be available at http://localhost:3000

## Project Structure

```
src/
  ├── components/     # Reusable UI components
  ├── contexts/       # React contexts (auth, etc.)
  ├── lib/           # API client and utilities
  ├── pages/         # Next.js pages
  └── styles/        # Global styles
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Technologies Used

- Next.js - React framework
- TypeScript - Type safety
- Tailwind CSS - Styling
- React Query - Data fetching and caching
- Chart.js - Data visualization
- React Hook Form - Form handling
- Axios - HTTP client

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.
